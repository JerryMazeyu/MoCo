from typing import List
from app.models.rules_zoo import BaseRule
from app.models.context_model import Context

class DistributionEngine:
    """
    Engine that applies a sequence of distribution rules on a given context.
    """
    def __init__(self, rules: List[BaseRule], context: Context):
        """
        Initialize the distribution engine with a set of rules.

        :param rules: List of DistributionRule instances.
        """
        self.rules = rules
        self.context = context

    def prepare(self) -> None:
        """
        Prepare the context for processing by the rules.

        :param context: DistributionContext to process.
        """
        self.context.base_info["max_oil_barrels"] = int(self.context.conf.BUSINESS.CAR["总收油量"] / self.context.conf.BUSINESS.CAR["桶每吨"] / self.context.conf.BUSINESS.CAR["比率"])


    def run(self, context: Context) -> None:
        """
        Run all the rules sequentially on the distribution context.

        :param context: DistributionContext to process.
        """
        for rule in self.rules:
            rule.apply(context)
