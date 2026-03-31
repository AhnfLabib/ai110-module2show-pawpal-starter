# PawPal+ — Class diagram (Mermaid)

Updated to reflect the current implementation in `pawpal_system.py` (recurrence via `TaskFrequency` + `due_day`, task time sorting, multi-pet brain utilities, and lightweight conflict warnings in `DailyPlan.warnings`).

```mermaid
classDiagram
    direction TB

    class Owner {
        +str name
        +dict preferences
        +List~Pet~ pets
        +add_pet(pet) None
        +get_pet(name) Pet
        +all_tasks() List~CareTask~
        +__str__() str
    }

    class Pet {
        +str name
        +str species
        +Dict details
        +List~CareTask~ tasks
        +add_task(task) None
        +get_task(task_id) CareTask
        +list_tasks(include_completed) List~CareTask~
        +__str__() str
    }

    class TaskFrequency {
        <<enumeration>>
        once
        daily
        weekly
        as_needed
    }

    class CareTask {
        +str title
        +int duration_minutes
        +str priority
        +str time
        +str pet_name
        +str id
        +str notes
        +TaskFrequency frequency
        +date due_day_optional
        +bool completed
        +date last_completed_day_optional
        +is_due_on(day) bool
        +mark_completed(day_optional) CareTask_optional
        -_spawn_next_instance(due_day) CareTask
        +mark_incomplete() None
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
        +List~str~ warnings
        +summary() str
        +iter_with_reasons()
    }

    class Scheduler {
        +preview(owner, pet, tasks, constraint) Dict
        +build_plan(owner, pet, tasks, constraint) DailyPlan
        -_detect_time_conflicts(items, default_pet_name) List~str~
        -_sort_candidates(tasks, owner, pet, constraint) List~CareTask~
        -_pack_into_budget(tasks, minutes) tuple
        -_explain_choice(task, context) str
    }

    class PawPalBrain {
        +Owner owner
        +add_pet(pet) None
        +add_task_to_pet(pet_name, task) None
        +pets() List~Pet~
        +tasks_for_pet(pet_name, include_completed) List~CareTask~
        +all_tasks(include_completed) List~CareTask~
        +tasks_grouped_by_pet(include_completed) Dict
        +filter_tasks(completed_optional, pet_name_optional, sort_by_time) List~CareTask~
    }

    class TimeHelpers {
        <<utility>>
        +_hhmm_sort_key(value) Tuple~int,int~
        +sort_tasks_by_time(tasks) List~CareTask~
    }

    Owner "1" --> "0..*" Pet : owns
    Pet "1" --> "0..*" CareTask : has
    PawPalBrain "1" --> "1" Owner : wraps
    Scheduler ..> DailyPlan : produces
    Scheduler ..> Owner : reads
    Scheduler ..> Pet : reads
    Scheduler ..> CareTask : reads
    Scheduler ..> DailyConstraint : reads
    DailyPlan "1" *-- "1..*" PlanItem : contains
    PlanItem --> CareTask : references
    CareTask --> TaskFrequency : frequency
    Scheduler ..> TimeHelpers : uses
    PawPalBrain ..> TimeHelpers : uses
```
