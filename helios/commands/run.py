from rich.console import Console

from ..services.claude import run_claude
from ..services.cost import calculate_cost
from ..services.db import init_db, insert_event
from ..services.git import get_current_feature

console = Console()


def run(prompt: str) -> None:
    init_db()
    feature = get_current_feature()

    result = run_claude(prompt)
    cost = calculate_cost(result.tokens_in, result.tokens_out, result.model)

    insert_event(
        feature=feature,
        model=result.model,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        total_tokens=result.total_tokens,
        cost=cost,
    )

    console.print(result.response)
    console.print()
    console.print(
        f"[dim]\\[helios] feature={feature} "
        f"tokens={result.total_tokens:,} "
        f"cost=${cost:.4f}[/dim]"
    )
