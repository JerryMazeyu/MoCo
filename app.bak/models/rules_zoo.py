from abc import ABC, abstractmethod
from app.models.context_model import Context

class BaseRule(ABC):
    """
    Abstract base class for distribution rules.
    """
    @abstractmethod
    def apply(self, context: Context) -> None:
        """
        Apply the rule to the distribution context.
        
        :param context: DistributionContext instance containing restaurants, vehicles, and assignments.
        """
        pass

    @abstractmethod
    def desc(self) -> str:
        """
        Return a description of the rule.
        """
        pass

class RegionMatchingRule(BaseRule):
    """
    Rule to filter restaurants for each vehicle based on matching district.
    """
    def apply(self, context: Context) -> None:
        for vehicle in context.vehicles:
            # Filter restaurants that are in the same district as the vehicle
            valid_restaurants = [r for r in context.restaurants if r.district == vehicle.district]
            # Initialize assignment list for this vehicle if not exists
            context.assignments.setdefault(vehicle.license_plate, [])
            # Save the filtered restaurants with initial assigned barrels = 0
            context.assignments[vehicle.license_plate] = [
                {"restaurant": r, "assigned_barrels": 0} for r in valid_restaurants
            ]

class CapacityRule(BaseRule):
    """
    Rule to assign the maximum number of barrels that can be collected from a restaurant,
    based on the restaurant's type (assumed to directly indicate capacity).
    """
    def apply(self, context: Context) -> None:
        for vehicle_plate, assignment_list in context.assignments.items():
            for assignment in assignment_list:
                restaurant = assignment["restaurant"]
                # Assume restaurant_type directly represents the maximum barrels collectable from the restaurant
                assignment["max_barrels"] = restaurant.restaurant_type
                # For illustration, we can initially set the assigned barrels to be the max available
                # (后续可结合车辆限制、总桶数等规则进行调整)
                assignment["assigned_barrels"] = restaurant.restaurant_type