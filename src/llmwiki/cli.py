import os
import asyncio
import click
import subprocess
import shutil
import time
import sys
import signal
import uuid
from rich.console import Console

from llmwiki.ingest import Processor
from llmwiki.gardener import Gardener, Reflector, QAEngine, Evolver, Writer, Maintainer
from llmwiki.gardener.dispatcher import Dispatcher
from llmwiki.utils import settings, Settings, ensure_vault_initialized, set_trace_id, set_task_type

console = Console()

@click.group()
@click.option('--config', type=click.Path(exists=True), help="Path to llmwiki.toml config file.")
@click.option('--vault', help="Path to the Obsidian vault.")
@click.pass_context
def cli(ctx, config, vault):
    """
    LLMWiki: A persistent, compounding knowledge codebase.
    """
    if config or vault:
        ctx.obj = Settings.load(config)
        if vault:
            ctx.obj.paths.vault = vault
    elif ctx.obj is None:
        ctx.obj = settings

    ensure_vault_initialized(ctx.obj.paths.vault)

def check_dependency(name):
    """Checks if a command-line dependency is installed."""
    import shutil
    return shutil.which(name) is not None

def sync_to_quartz(vault_path):
    if os.path.exists("quartz"):
        pages_dir = os.path.join(vault_path, "pages")
        quartz_content = os.path.join("quartz", "content")
        os.makedirs(quartz_content, exist_ok=True)
        existing_entries = set(os.listdir(quartz_content))
        source_entries = set(os.listdir(pages_dir)) if os.path.exists(pages_dir) else set()

        for stale_entry in existing_entries - source_entries:
            stale_path = os.path.join(quartz_content, stale_entry)
            if os.path.isdir(stale_path):
                shutil.rmtree(stale_path)
            else:
                os.remove(stale_path)

        for entry in source_entries:
            source_path = os.path.join(pages_dir, entry)
            target_path = os.path.join(quartz_content, entry)
            if os.path.isdir(source_path):
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)
            else:
                shutil.copy2(source_path, target_path)

@cli.command()
@click.argument('source', type=str)
@click.option('--provider', help="LLM provider (openai, gemini-cli, codex-cli).")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def ingest(config: Settings, source: str, provider: str, model: str, base_url: str, api_key: str):
    """
    Ingest a file or URL into the LLMWiki vault and trigger the Gardener.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("INGEST")
    
    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    
    vault_path = config.paths.vault
    console.print(f"[bold blue]Ingesting:[/bold blue] {source} into {vault_path} (via {provider})")
    
    skip_ext = provider.endswith("-cli")
    processor = Processor(vault_path=vault_path)
    dest, text, needs_processing = processor.process_file(source, skip_extraction=skip_ext)
    
    if not needs_processing:
        console.print(f"[yellow]Source already processed:[/yellow] {source}")
        return

    console.print(f"[bold green]Successfully ingested:[/bold green] {dest}")
    if text:
        console.print(f"Extracted {len(text)} characters.")
    
    console.print("[bold blue]Gardening...[/bold blue]")
    
    gardener = Gardener(
        provider=provider,
        model_name=model, 
        base_url=base_url, 
        api_key=api_key, 
        vault_path=vault_path
    )
    
    # Use the sanitized filename for the Gardener
    filename = os.path.basename(dest)
    try:
        asyncio.run(gardener.process_new_source(filename, extracted_text=text, file_path=dest))
        processor.mark_as_done(dest)
        sync_to_quartz(vault_path)
        console.print("[bold green]Gardening complete![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Gardening failed:[/bold red] {str(e)}")
        processor.mark_as_failed(dest)

@cli.command()
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--concurrency', type=int, help="Number of files to process in parallel.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def sync(config: Settings, provider: str, model: str, concurrency: int, base_url: str, api_key: str):
    """
    Scan vault/raw for new files and process them in parallel.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("SYNC")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    concurrency = concurrency or config.ingest.concurrency
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    console.print(f"[bold blue]Syncing vault (concurrency={concurrency}, provider={provider})...[/bold blue]")
    processor = Processor(vault_path=vault_path)
    raw_path = os.path.join(processor.vault_path, "raw")
    
    if not os.path.exists(raw_path):
        console.print(f"[yellow]Raw directory not found: {raw_path}[/yellow]")
        return

    files = os.listdir(raw_path)
    to_process = []
    
    for filename in files:
        file_path = os.path.join(raw_path, filename)
        if os.path.isdir(file_path):
            continue
        to_process.append(file_path)

    async def worker(file_path, sem):
        async with sem:
            set_trace_id(str(uuid.uuid4())[:8])
            set_task_type("GARDEN")
            
            skip_ext = provider.endswith("-cli")
            dest, text, needs_processing = processor.process_file(file_path, skip_extraction=skip_ext)
            if needs_processing:
                sanitized_name = os.path.basename(dest)
                console.print(f"[bold blue]Gardening new file:[/bold blue] {sanitized_name}")
                gardener = Gardener(
                    provider=provider,
                    model_name=model, 
                    base_url=base_url, 
                    api_key=api_key, 
                    vault_path=vault_path
                )
                try:
                    await gardener.process_new_source(sanitized_name, extracted_text=text, file_path=dest)
                    processor.mark_as_done(dest)
                    return True
                except Exception as e:
                    console.print(f"[bold red]Gardening failed for {sanitized_name}:[/bold red] {str(e)}")
                    processor.mark_as_failed(dest)
            return False

    async def run_sync():
        sem = asyncio.Semaphore(concurrency)
        tasks = [worker(fp, sem) for fp in to_process]
        results = await asyncio.gather(*tasks)
        return sum(1 for r in results if r)

    processed_count = asyncio.run(run_sync())
    sync_to_quartz(vault_path)
    console.print(f"[bold green]Sync complete. Processed {processed_count} new files.[/bold green]")

@cli.command()
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def watch(config: Settings, model: str, provider: str, base_url: str, api_key: str):
    """
    Watch vault/raw for new files and process them automatically.
    """
    set_trace_id("watch-init")
    set_task_type("WATCH")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    processor = Processor(vault_path=vault_path)
    raw_path = os.path.join(processor.vault_path, "raw")
    
    if not os.path.exists(raw_path):
        os.makedirs(raw_path, exist_ok=True)

    # Heartbeat thread
    def heartbeat():
        from llmwiki.db.store import Store
        store = Store(vault_path)
        while True:
            store.set_heartbeat("watch")
            time.sleep(30)
    
    import threading
    threading.Thread(target=heartbeat, daemon=True).start()

    # Perform initial sync
    console.print(f"[bold blue]Performing initial sync of {raw_path}...[/bold blue]")
    files = os.listdir(raw_path)
    for filename in files:
        file_path = os.path.join(raw_path, filename)
        if os.path.isdir(file_path): continue
        
        set_trace_id(str(uuid.uuid4())[:8])
        set_task_type("INGEST")
        
        skip_ext = provider.endswith("-cli")
        dest, text, needs_processing = processor.process_file(file_path, skip_extraction=skip_ext)
        if needs_processing:
            sanitized_name = os.path.basename(dest)
            console.print(f"[bold blue]Gardening existing file:[/bold blue] {sanitized_name}")
            gardener = Gardener(
                provider=provider,
                model_name=model, 
                base_url=base_url, 
                api_key=api_key, 
                vault_path=vault_path
            )
            try:
                asyncio.run(gardener.process_new_source(sanitized_name, extracted_text=text, file_path=dest))
                processor.mark_as_done(dest)
            except Exception as e:
                console.print(f"[bold red]Gardening failed for {sanitized_name}:[/bold red] {str(e)}")
                processor.mark_as_failed(dest)

    from watchfiles import watch as watch_files
    console.print(f"[bold blue]Watching {vault_path}/raw for changes (provider={provider})...[/bold blue]")
    
    for changes in watch_files(raw_path):
        for change_type, file_path in changes:
            if change_type in [1, 2]: # Added or Modified
                set_trace_id(str(uuid.uuid4())[:8])
                set_task_type("INGEST")
                
                filename = os.path.basename(file_path)
                console.print(f"[bold blue]Detected change in: {filename}[/bold blue]")
                
                skip_ext = provider.endswith("-cli")
                dest, text, needs_processing = processor.process_file(file_path, skip_extraction=skip_ext)
                if needs_processing:
                    sanitized_name = os.path.basename(dest)
                    gardener = Gardener(
                        provider=provider,
                        model_name=model, 
                        base_url=base_url, 
                        api_key=api_key, 
                        vault_path=vault_path
                    )
                    try:
                        asyncio.run(gardener.process_new_source(sanitized_name, extracted_text=text, file_path=dest))
                        processor.mark_as_done(dest)
                        sync_to_quartz(vault_path)
                        console.print(f"[bold green]Processed {sanitized_name}![/bold green]")
                    except Exception as e:

                        console.print(f"[bold red]Gardening failed for {sanitized_name}:[/bold red] {str(e)}")
                        processor.mark_as_failed(dest)

@cli.command()
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def reflect(config: Settings, provider: str, model: str, base_url: str, api_key: str):
    """
    Perform deep thinking over the vault to generate Mental Models.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("REFLECT")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    console.print(f"[bold blue]Reflecting on knowledge vault...[/bold blue] (via {provider})")
    reflector = Reflector(
        provider=provider,
        model_name=model, 
        base_url=base_url, 
        api_key=api_key, 
        vault_path=vault_path
    )
    try:
        asyncio.run(reflector.reflect())
        console.print("[bold green]Reflection complete! New insights added to models/.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Reflection failed:[/bold red] {str(e)}")

@cli.command()
@click.argument('question')
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def ask(config: Settings, question: str, provider: str, model: str, base_url: str, api_key: str):
    """
    Ask a question based on the knowledge in the vault.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("QA")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    console.print(f"[bold blue]Question:[/bold blue] {question} (via {provider})")
    qa = QAEngine(
        provider=provider,
        model_name=model, 
        base_url=base_url, 
        api_key=api_key, 
        vault_path=vault_path
    )
    try:
        answer = asyncio.run(qa.ask(question))
        sync_to_quartz(vault_path)
        console.print(f"\n[bold green]Answer:[/bold green]\n{answer}")
        console.print(f"\n[dim]Answer saved to {vault_path}/pages/qa/[/dim]")
    except Exception as e:
        console.print(f"[bold red]QA failed:[/bold red] {str(e)}")

@cli.command()
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def evolve(config: Settings, provider: str, model: str, base_url: str, api_key: str):
    """
    Autonomous maintenance: merge duplicates, fix links, and optimize summaries.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("EVOLVE")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    console.print(f"[bold blue]Evolving knowledge vault...[/bold blue] (via {provider})")
    evolver = Evolver(
        provider=provider,
        model_name=model, 
        base_url=base_url, 
        api_key=api_key, 
        vault_path=vault_path
    )
    try:
        report = asyncio.run(evolver.evolve())
        console.print(f"\n[bold green]Evolution Complete![/bold green]\n{report}")
    except Exception as e:
        console.print(f"[bold red]Evolution failed:[/bold red] {str(e)}")

@cli.command()
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def maintain(config: Settings, provider: str, model: str, base_url: str, api_key: str):
    """
    Audit the vault for contradictions, broken links, and errors.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("AUDIT")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    console.print(f"[bold blue]Auditing knowledge vault...[/bold blue] (via {provider})")
    maintainer = Maintainer(
        provider=provider,
        model_name=model, 
        base_url=base_url, 
        api_key=api_key, 
        vault_path=vault_path
    )
    try:
        report = asyncio.run(maintainer.maintain())
        console.print(f"\n[bold green]Audit Complete![/bold green]\n{report}")
    except Exception as e:
        console.print(f"[bold red]Audit failed:[/bold red] {str(e)}")

@cli.command()
@click.argument('topic')
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def brew(config: Settings, topic: str, provider: str, model: str, base_url: str, api_key: str):
    """
    Generate a comprehensive report or briefing on a topic.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("BREW")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    console.print(f"[bold blue]Brewing artifact for:[/bold blue] {topic} (via {provider})")
    writer = Writer(
        provider=provider,
        model_name=model, 
        base_url=base_url, 
        api_key=api_key, 
        vault_path=vault_path
    )
    try:
        path = asyncio.run(writer.brew(topic))
        console.print(f"[bold green]Artifact generated successfully![/bold green]")
        console.print(f"Location: {path}")
    except Exception as e:
        console.print(f"[bold red]Brewing failed:[/bold red] {str(e)}")

@cli.command()
@click.argument('message')
@click.option('--provider', help="LLM provider.")
@click.option('--model', help="LLM model name.")
@click.option('--base-url', help="Custom base URL for OpenAI-compatible API.")
@click.option('--api-key', help="API key for the custom endpoint.")
@click.pass_obj
def chat(config: Settings, message: str, provider: str, model: str, base_url: str, api_key: str):
    """
    Talk to the LLMWiki Crew and orchestrate complex tasks.
    """
    set_trace_id(str(uuid.uuid4())[:8])
    set_task_type("CHAT")

    provider = provider or config.llm.provider
    model = model or config.llm.model
    base_url = base_url or config.llm.base_url
    api_key = api_key or config.llm.api_key
    vault_path = config.paths.vault

    console.print(f"[bold blue]You:[/bold blue] {message} (via {provider})")
    dispatcher = Dispatcher(
        provider=provider,
        model_name=model, 
        base_url=base_url, 
        api_key=api_key, 
        vault_path=vault_path
    )
    try:
        response = asyncio.run(dispatcher.dispatch(message))
        console.print(f"\n[bold green]Crew:[/bold green]\n{response}")
    except Exception as e:
        console.print(f"[bold red]Chat failed:[/bold red] {str(e)}")

@cli.command()
@click.option('--port', type=int, help="Port to run the dashboard on.")
@click.option('--host', help="Host to bind the dashboard to.")
@click.pass_obj
def dashboard(config: Settings, port: int, host: str):
    """
    Start the LLMWiki Observability Dashboard (FastAPI).
    """
    set_trace_id("dash-init")
    set_task_type("SYSTEM")

    port = port or config.dashboard.port
    host = host or config.dashboard.host
    vault_path = config.paths.vault
    console.print(f"[bold blue]Starting FastAPI dashboard on {host}:{port}...[/bold blue]")
    
    # Heartbeat thread
    def heartbeat():
        from llmwiki.db.store import Store
        store = Store(vault_path)
        while True:
            store.set_heartbeat("dashboard")
            time.sleep(30)
    
    import threading
    threading.Thread(target=heartbeat, daemon=True).start()

    import uvicorn
    os.environ["LLMWIKI_VAULT"] = vault_path
    uvicorn.run("llmwiki.dashboard.server:app", host=host, port=port, log_level="info")

@cli.command()
@click.pass_obj
def gateway(config: Settings):
    """
    Start the Multi-Channel Gateway (Telegram, Feishu, etc.).
    """
    if not config.gateway.enabled:
        console.print("[yellow]Gateway is disabled in config. Enable it in llmwiki.toml to run.[/yellow]")
        return

    console.print("[bold blue]Starting LLMWiki Gateway...[/bold blue]")
    from llmwiki.gateway.manager import GatewayManager
    from llmwiki.gateway.channels.telegram import TelegramChannel
    from llmwiki.gateway.channels.rest import RestChannel
    
    gm = GatewayManager(config)
    
    # Load Telegram if configured
    if config.gateway.telegram.token:
        tg = TelegramChannel(
            token=config.gateway.telegram.token,
            allowed_users=config.gateway.telegram.allowed_users
        )
        gm.register_channel(tg)

    # Load REST if configured
    if config.gateway.rest.enabled:
        rest = RestChannel(
            host=config.gateway.rest.host,
            port=config.gateway.rest.port,
            api_key=config.gateway.rest.api_key
        )
        gm.register_channel(rest)
    
    # Run manager
    try:
        asyncio.run(gm.start())
    except KeyboardInterrupt:
        console.print("\n[yellow]Gateway shutting down...[/yellow]")

@cli.command()
@click.option('--interval', type=int, help="Maintenance interval in seconds.")
@click.pass_obj
def maintenance(config: Settings, interval: int):
    """
    Run periodic background maintenance (reflect, evolve, maintain).
    """
    interval = interval or config.runtime.maintenance_interval_s
    vault_path = config.paths.vault
    console.print(f"[bold blue]Starting maintenance service (interval={interval}s)...[/bold blue]")
    
    from llmwiki.db.store import Store
    store = Store(vault_path)

    while True:
        set_trace_id(str(uuid.uuid4())[:8])
        set_task_type("MAINTAIN")
        
        store.set_heartbeat("maintenance")
        try:
            console.print("[dim]Running reflection...[/dim]")
            reflector = Reflector(
                provider=config.llm.provider,
                model_name=config.llm.model, 
                base_url=config.llm.base_url, 
                api_key=config.llm.api_key, 
                vault_path=vault_path
            )
            asyncio.run(reflector.reflect())
            
            console.print("[dim]Running evolution...[/dim]")
            evolver = Evolver(
                provider=config.llm.provider,
                model_name=config.llm.model, 
                base_url=config.llm.base_url, 
                api_key=config.llm.api_key, 
                vault_path=vault_path
            )
            asyncio.run(evolver.evolve())

            console.print("[dim]Running audit...[/dim]")
            maintainer = Maintainer(
                provider=config.llm.provider,
                model_name=config.llm.model, 
                base_url=config.llm.base_url, 
                api_key=config.llm.api_key, 
                vault_path=vault_path
            )
            asyncio.run(maintainer.maintain())
            
            sync_to_quartz(vault_path)
            console.print("[bold green]Maintenance cycle complete.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Maintenance cycle failed:[/bold red] {str(e)}")
        
        time.sleep(interval)

@cli.command()
@click.option('--port', type=int, help="Port to run the Quartz server on.")
@click.option('--host', help="Host to bind the Quartz server to.")
@click.pass_obj
def server(config: Settings, port: int, host: str):
    """
    Run the Quartz preview server.
    """
    set_trace_id("quartz-init")
    set_task_type("SYSTEM")

    port = port or config.server.port
    host = host or config.server.host
    vault_path = config.paths.vault
    console.print(
        f"[bold blue]Starting Quartz server on port {port} (requested host: {host})...[/bold blue]"
    )
    
    from llmwiki.db.store import Store
    store = Store(vault_path)
    
    def heartbeat():
        while True:
            store.set_heartbeat("server")
            time.sleep(30)
    
    import threading
    threading.Thread(target=heartbeat, daemon=True).start()

    try:
        if not check_dependency("npx"):
            console.print("[bold red]Error: npx is not installed.[/bold red] LLMWiki requires Node.js/npm for the Quartz visualization layer.")
            return

        sync_to_quartz(vault_path)
        # Quartz v4's build CLI supports --port but not --host.
        subprocess.run(
            ["npx", "quartz", "build", "--serve", "--port", str(port)],
            cwd="quartz",
            check=True,
        )
    except Exception as e:
        console.print(f"[bold red]Quartz server failed:[/bold red] {str(e)}")

@cli.command()
@click.pass_context
def up(ctx):
    """
    Start all LLMWiki services simultaneously.
    """
    console.print("[bold blue]Starting all LLMWiki services...[/bold blue]")
    config = ctx.obj
    
    services = [
        ["llmwiki", "watch"],
        ["llmwiki", "dashboard"],
        ["llmwiki", "maintenance"],
        ["llmwiki", "server"]
    ]
    
    if config.gateway.enabled:
        services.append(["llmwiki", "gateway"])
    
    if config.paths.vault != "vault":
        for s in services:
            s.insert(1, "--vault")
            s.insert(2, config.paths.vault)

    processes = []
    
    def signal_handler(sig, frame):
        console.print("\n[yellow]Shutting down services...[/yellow]")
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        for cmd in services:
            p = subprocess.Popen(cmd)
            processes.append(p)
        
        while True:
            for p in processes:
                if p.poll() is not None:
                    console.print(f"[bold red]Service {p.args} exited with code {p.returncode}[/bold red]")
            time.sleep(5)
    except Exception as e:
        console.print(f"[bold red]Orchestrator error: {e}[/bold red]")
        for p in processes:
            p.terminate()

@cli.command()
@click.pass_obj
def build(config: Settings):
    """
    Build the Quartz site.
    """
    if not check_dependency("npx"):
        console.print("[bold red]Error: npx is not installed.[/bold red] LLMWiki requires Node.js/npm for the Quartz visualization layer.")
        return

    console.print("[bold blue]Building Quartz site...[/bold blue]")
    try:
        sync_to_quartz(config.paths.vault)
        subprocess.run(["npx", "quartz", "build"], cwd="quartz", check=True)
        console.print("[bold green]Quartz site built successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Quartz build failed:[/bold red] {str(e)}")

@cli.command()
@click.pass_obj
def map(config: Settings):
    """
    Generate a weighted Mermaid.js knowledge graph of the vault.
    """
    from llmwiki.db.store import Store
    store = Store(config.paths.vault)
    
    conn = store._get_conn()
    cur = conn.execute("SELECT source, target, weight, type FROM links")
    links = cur.fetchall()
    
    mermaid = "graph LR\n"
    for src, tgt, weight, ltype in links:
        s = src.split('/')[-1].replace('-', ' ')
        t = tgt.split('/')[-1].replace('-', ' ')
        
        # Mermaid styling based on weight
        # Thicker lines for core relationships, dashed for mentions
        if weight >= 1.0:
            edge = " == " + ltype + " ==> "
        elif weight <= 0.3:
            edge = " -. " + ltype + " .-> "
        else:
            edge = " -- " + ltype + " --> "
            
        mermaid += f"    id{hash(src) % 10000}[{s}]{edge}id{hash(tgt) % 10000}[{t}]\n"
    
    path = os.path.join(config.paths.vault, "pages", "graph.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"---\ntitle: \"Knowledge Graph\"\n---\n\n# 🕸️ Knowledge Graph\n\n```mermaid\n{mermaid}\n```\n")
    
    console.print(f"[bold green]Graph generated at {path}[/bold green]")

if __name__ == '__main__':
    cli()
