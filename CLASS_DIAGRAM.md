classDiagram
    direction TB

    class Owner {
        +str name
        +dict preferences
        +__str__() str
    }

    class Pet {
        +str name
        +str species
        +__str__() str
    }

    class CareTask {
        +str title
        +int duration_minutes
        +str priority
        +str id
        +str notes
        +priority_score() int
        +__lt__(other) bool
    }

    class DailyConstraint {
        +int minutes_available
        +date day
        +__str__() str
    }

    class PlanItem {
        +CareTask task
        +str reason
        +int order_index
        +int start_minute_optional
    }

    class DailyPlan {
        +List~PlanItem~ items
        +int total_minutes_used
        +int leftover_minutes
        +List~CareTask~ skipped_tasks
        +summary() str
        +iter_with_reasons()
    }

    class Scheduler {
        +build_plan(owner, pet, tasks, constraint) DailyPlan
        -_sort_candidates(tasks) list
        -_pack_into_budget(tasks, minutes) tuple
        -_explain_choice(task, context) str
    }

    Owner "1" --> "0..*" Pet : cares_for
    Scheduler ..> DailyPlan : produces
    Scheduler ..> Owner : reads
    Scheduler ..> Pet : reads
    Scheduler ..> CareTask : reads
    Scheduler ..> DailyConstraint : reads
    DailyPlan "1" *-- "1..*" PlanItem : contains
    PlanItem --> CareTask : references

