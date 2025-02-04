from typing import List
from app.models.rule_model import BaseRule
from app.models.context_model import Context

class DistributionEngine:
    """
    Engine that applies a sequence of distribution rules on a given context.
    """
    def __init__(self, rules: List[BaseRule]):
        """
        Initialize the distribution engine with a set of rules.

        :param rules: List of DistributionRule instances.
        """
        self.rules = rules

    def run(self, context: Context) -> None:
        """
        Run all the rules sequentially on the distribution context.

        :param context: DistributionContext to process.
        """
        for rule in self.rules:
            rule.apply(context)