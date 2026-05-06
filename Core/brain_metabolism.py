import os

from .genotype import Gene
from .phenotype import Phenotype


class Brain:
    """Thin runtime identity shell.

    Daily summary reflection is outside the live runtime after the raw-only Neo4j reboot.
    The live graph keeps Brain as a lightweight compatibility object only.
    """

    def __init__(self):
        self.gene = Gene()
        self.ego = {}
        self.body = Phenotype(self.gene)
        self.local_model = os.getenv("ANIMA_MAIN_MODEL", "gemma4:e4b").strip() or "gemma4:e4b"
        print(f"[Brain] thin runtime shell ready: {self.local_model}")

    def reflect_on_day(self, target_date):
        return None
