"""
Simple lever tracker.

This is a starter version. It maps checkbox history to L1-L6 state.
"""


def determine_lever_state(tried_retention: bool, tried_selectivity: bool, tried_efficiency: bool, tried_gradient: bool) -> dict:
    if tried_gradient and not (tried_retention or tried_selectivity or tried_efficiency):
        return {
            "state": "L6",
            "next_action": "Restart with isocratic optimisation before gradient changes.",
        }

    if tried_retention and tried_selectivity and tried_efficiency and tried_gradient:
        return {
            "state": "L5",
            "next_action": "Escalate to method redevelopment.",
        }

    if tried_retention and tried_selectivity and tried_efficiency:
        return {
            "state": "L4",
            "next_action": "Try gradient elution: optimise gradient slope or add isocratic holds.",
        }

    if tried_retention and tried_selectivity:
        return {
            "state": "L3",
            "next_action": "Try efficiency: smaller particle size, longer column, or check extra-column volume.",
        }

    if tried_retention:
        return {
            "state": "L2",
            "next_action": "Try selectivity: adjust pH, organic modifier, or column chemistry.",
        }

    return {
        "state": "L1",
        "next_action": "Try retention first: adjust organic solvent percentage.",
    }
