"""Política determinística independente do modelo supervisionado."""
from dataclasses import asdict, dataclass
import math

CAPABILITIES = ("read_input", "write_output")


@dataclass(frozen=True)
class Budget:
    memory_mb: int = 256
    wall_seconds: float = 5.0
    cpu_seconds: int = 3
    output_mb: int = 4
    read_input: bool = True
    write_output: bool = True

    def __post_init__(self):
        for name in ("memory_mb", "cpu_seconds", "output_mb"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name}: inteiro positivo obrigatório")
        if not math.isfinite(self.wall_seconds) or self.wall_seconds <= 0:
            raise ValueError("wall_seconds: número finito positivo obrigatório")

    def to_dict(self):
        return asdict(self)


def authorize(recommendation: dict, ceiling: Budget) -> Budget:
    """Nunca permite rede, novos mounts ou recursos acima do teto externo."""
    unknown = set(recommendation) - {"memory_mb", "wall_seconds", *CAPABILITIES}
    if unknown:
        raise ValueError(f"Capacidade não suportada: {sorted(unknown)}")
    memory = float(recommendation.get("memory_mb", ceiling.memory_mb))
    wall = float(recommendation.get("wall_seconds", ceiling.wall_seconds))
    if not math.isfinite(memory) or not math.isfinite(wall) or min(memory, wall) <= 0:
        raise ValueError("Recomendação inválida")
    for cap in CAPABILITIES:
        if cap in recommendation and type(recommendation[cap]) is not bool:
            raise ValueError(f"{cap}: booleano obrigatório")
    return Budget(
        memory_mb=min(ceiling.memory_mb, max(16, math.ceil(memory))),
        wall_seconds=min(ceiling.wall_seconds, max(0.15, wall)),
        cpu_seconds=ceiling.cpu_seconds,
        output_mb=ceiling.output_mb,
        read_input=ceiling.read_input and recommendation.get("read_input", False),
        write_output=ceiling.write_output and recommendation.get("write_output", False),
    )
