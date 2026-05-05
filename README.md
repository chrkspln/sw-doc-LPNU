The system being modelled is Microsoft Project, a real piece of project-planning software where a manager builds a plan by adding tasks and resources, defining milestones, hooking everything together with dependencies, and then validating the result. The lab asks for four UML diagrams covering this from different angles: a use case diagram for who interacts with the system and what they can do, a class diagram for the static structure of plan elements, an activity diagram for the workflow of creating a plan, and a sequence diagram for the runtime conversation between objects when tasks and resources are saved to the database.



The four diagrams show the same system from different angles. Use case is the user's view (what can be done). Class is the architect's view (what types exist and how they relate). Activity is the workflow view (in what order things happen). Sequence is the runtime view (who talks to whom, and when). A reviewer expects them to be internally consistent: a class mentioned in the sequence diagram should also appear in the class diagram, an action in the activity diagram should map to some use case, and so on. Where there are inconsistencies, I want to be ready to acknowledge them rather than dance around.



\## A Quick Notation Primer



Before walking through each diagram, here's the cheat sheet for what every shape means. UML notation is mostly intuitive once you know the alphabet, but professors do ask "what does this exact symbol mean," so being precise matters.



\### Use case diagrams



The \*\*stick figure\*\* is an \*actor\*. An actor is anything outside the system that interacts with it. Usually a person — Project Manager, Team Member, Administrator — but it can also be another system, like Notification Service or Calendar Integration. Actors don't have to be human, and in real-world architectures the non-human ones often matter just as much.



The \*\*oval\*\* is a \*use case\*. It represents a goal a user wants to accomplish: "Add Task," "Validate Plan," "Export Plan." The verb-object naming pattern is intentional — a use case is always something that gets done.



The \*\*rectangle around the ovals\*\* is the \*system boundary\*. Everything inside is part of the system being built. Actors stay outside.



A \*\*solid line\*\* between an actor and a use case is an \*association\*. It just means "this actor participates in this use case." It carries no extra meaning.



A \*\*dashed arrow\*\* between two use cases is a \*dependency relationship\*, and the label on top tells you what kind. The keyword `«include»` means the source use case always invokes the target one — every time the source runs, the target runs. Save Plan «include» Calculate Critical Path means every time you save, the critical path gets recalculated, no exceptions. The keyword `«extend»` means the source \*may\* be enriched by the target under some condition. Validate Plan «extend» Resolve Overallocation means resolving an overallocation only happens when validation actually finds one. The default behavior of validation is just to report; the extension only kicks in conditionally.



The arrow direction trips a lot of people up, and professors often ask specifically about it. For include, the arrow points from the host \*to\* the included one — the host knows it includes the target. For extend, the arrow points from the extension \*to the host\* — the extension says "I extend you," but the host doesn't know it's being extended. The trick I use to remember: the dashed arrow always points to the use case that doesn't know about the relationship.



\### Class diagrams



A \*\*rectangle with three compartments\*\* is a \*class\*. The top compartment holds the class name, the middle holds attributes (data), and the bottom holds methods (behavior). When the class name is in \*italics\*, the class is \*abstract\* — meaning it cannot be instantiated directly, only its subclasses can. In my diagram, `Resource` has its name in italics for exactly this reason.



The `-` and `+` symbols in front of attributes and methods are \*visibility markers\*. Minus means private (only this class can access), plus means public (anyone can access). Every attribute in my diagram is private, which is the visible expression of encapsulation — outside code can't read or write a Project's `name` directly, it has to go through the methods.



A \*\*solid line with a hollow triangle\*\* on one end is \*inheritance\* (also called generalization). The triangle points to the parent class. Milestone has a triangle pointing to Task, meaning Milestone is a kind of Task and inherits everything Task has.



A \*\*solid line with a filled diamond\*\* is \*composition\*. The diamond sits at the container end, and the relationship means strong ownership — the contained part cannot exist without its container. Project ◆— Task means tasks live and die with the project: delete the project, the tasks go with it.



A \*\*solid line with a hollow diamond\*\* is \*aggregation\*. Same shape, but the diamond is hollow, and the relationship is weaker. The contained part can exist independently of the container. Project ◇— Resource means a project uses resources, but the resources themselves — a person, a piece of equipment — exist whether or not this particular project does.



A \*\*plain solid line\*\* with no diamonds and no arrowheads is a regular \*association\*. It just says "these two are connected." The numbers on each end (`1`, `0..\*`, `1..\*`) are \*multiplicities\* — they say how many of one connect to how many of the other. `0..\*` means "zero or more."



A \*\*dashed arrow\*\* is a \*dependency\*. It's the weakest "uses" relationship in UML — class A calls a method on class B, or A takes B as a parameter, but A doesn't store or own B. ProjectService and ValidationService both depend on Project this way: they operate on it but don't own one.



The \*\*dashed line connecting to a separate class box hanging off another association line\*\* is an \*association class\*. It's the proper way to show that the relationship itself has data. Task–Resource is a many-to-many relationship, but each Task–Resource pair has its own units, work, and cost. That data doesn't belong to the Task or the Resource alone — it belongs to the \*pairing\*. The class hanging off the association line, Assignment, holds it.



\### Activity diagrams



The \*\*filled black circle\*\* is the \*start node\*. There's only one of these per diagram, and it's where execution begins.



The \*\*filled black circle inside a ring\*\* (the bull's-eye) is the \*end node\*. It's where the activity finishes.



A \*\*rounded rectangle\*\* is an \*action\* or \*activity\* — a thing that happens. "Authenticate," "Create Project," "Validate Plan."



A \*\*rhombus\*\* (or hexagon, in PlantUML's default rendering) plays two roles depending on how arrows attach to it. With one arrow in and several out, it's a \*decision\* — a branching point, with `\[yes]` / `\[no]` or other guard labels on the outgoing arrows. With several arrows in and one out, it's a \*merge\* — paths converging back together.



The \*\*thick black horizontal bar\*\* is a \*fork\* (one in, several out — flow splits into parallel branches that all run at once) or a \*join\* (several in, one out — flow waits for all incoming branches before continuing). Fork and join always come in matched pairs; an unmatched one is a modeling error.



Plain arrows are control flow — they show the order things happen.



\### Sequence diagrams



Each \*\*box at the top\*\* is a \*participant\*, also called a \*lifeline\*. It's an object or actor that takes part in the interaction. The vertical \*\*dashed line\*\* dropping down from each box represents that participant's existence over time — and time flows downward in a sequence diagram, which is the most important convention to internalize.



A \*\*stick figure\*\* at the top means the participant is an actor (a human user). A \*\*cylinder\*\* symbol means the participant is a database — an external persistence boundary, distinct from internal objects.



A \*\*solid arrow with a filled arrowhead\*\* is a \*synchronous message\* — a method call where the sender waits for the result. A \*\*dashed arrow with an open arrowhead\*\* is a \*return message\*, the value coming back from a synchronous call. You don't strictly have to draw return arrows, but doing so makes the diagram much clearer, especially when the return carries something important like a `projectId`.



A \*\*thin vertical rectangle\*\* sitting on a lifeline is an \*activation bar\* (also called an execution specification). It shows when that object is actively executing — a method on it is currently running. It's optional, but it makes the diagram easier to read.



The \*\*labeled rectangular frames\*\* that wrap parts of the diagram are \*combined fragments\*. The label in the top-left tab tells you what kind. `loop` means the enclosed messages repeat, with the loop's condition shown in the guard. `alt` means alternative paths — only one of the sub-regions executes, and the sub-regions are separated by a dashed horizontal line. My alt has `\[available]` on top and `\[overallocated]` on the bottom, so exactly one of those runs depending on the validation result. `opt` means optional — the enclosed messages either run as a block or get skipped entirely. There are other fragment types in UML (par for parallel, ref for referencing another diagram), but those three cover everything in my work.



\## Use Case Diagram — What's There and Why



The use case diagram captures the system from the user's point of view. It answers the question "what can be done with this system, and by whom?" It says nothing about how things are implemented or in what order they happen — those are jobs for the other three diagrams.



My diagram has five actors. Project Manager is the primary actor, the role almost everything important goes through. They create the project, manage tasks and resources, assign work, validate the plan, and export it. Team Member is a secondary actor that exists for completeness; they can authenticate and view the tasks assigned to them, but they don't build the plan. Administrator handles user management, which is also peripheral but realistic — in any real system someone has to manage accounts. The two non-human actors on the right side, Notification Service and Calendar Integration, are external systems. They're worth showing because they explain where two of the use cases connect to the outside world.



The use cases inside the system boundary fall into a few logical groups even though they're not visually grouped on the diagram. There's a small authentication-and-setup cluster (Authenticate, Create Project, Configure Project Calendar). There's a task-management cluster (Add Task, Edit Task, Delete Task, Set Task Dependency, Define Milestone). There's a resource-management cluster (Add Resource, Edit Resource, Set Resource Cost, Set Resource Availability). There's a plan-assembly cluster (Assign Resource to Task, Validate Plan, Resolve Overallocation, Calculate Critical Path). And there's an output cluster (Save Plan, Export Plan, View Gantt Chart, Send Notifications, View Assigned Tasks).



The dashed arrows are the heart of what makes this a real UML diagram and not just a decorated list. Create Project «include» Authenticate means before any project can be created, the user must already be authenticated. The include is mandatory and unconditional. Save Plan «include» Calculate Critical Path means every successful save recalculates the critical path; the critical path isn't optional after a save. Add Resource «include» Set Resource Cost and «include» Set Resource Availability follow the same logic — when you add a resource, you have to specify both cost and availability, they're inseparable from the act of adding it.



The «extend» relationships work differently. Validate Plan «extend» Resolve Overallocation means the system tries to resolve overallocations \*only when\* validation finds one — most validations don't trigger this. Save Plan «extend» Send Notifications means notifications dispatch only when there's something worth notifying about. Add Task «extend» Set Task Dependency means dependencies are set only when the new task actually depends on an existing one — many tasks have no predecessors, and for those the extension never fires.



The textual use case description for "Create Project Plan" is in the supporting document. The lab specifically asks for it: "use cases must contain a description of all necessary components, including main flow and alternative paths and exceptions." The textual form has a fixed structure: the name, the actor, preconditions (what must be true before the use case starts), the main flow as a numbered sequence of steps, alternative flows (branches off the main flow, like step 7a if a resource is overallocated), exceptions (technical failures like a database write error), and postconditions (what's true after the use case ends). The numbered alternative-flow notation (4a, 5a, 7a, 8a) is the convention for "this is what happens if step 4 has a special situation" — the letter just means it's a branch off the same step.



If the professor asks why Administrator is in the diagram when the task is specifically about plan creation, the honest answer is completeness. A use case diagram is supposed to show all actors who interact with the system, not only the ones relevant to the highlighted use case. Removing Administrator would leave the picture of "who uses this system" incomplete. Both keeping and removing them is defensible — what's not defensible is having no answer when asked.



If they ask why Authenticate is a separate use case rather than just a precondition, the answer is that authentication has its own UI, its own failure modes, and its own implementation logic. It deserves to be a use case in its own right, and that's why so many other use cases include it.



\## Class Diagram — Why These Classes and These Relationships



The class diagram shows the static structure of the system: what types of objects exist and how they're connected. Unlike the activity or sequence diagrams, it has no notion of time. It's the architect's blueprint.



I split the classes into a domain layer and a service layer. The domain layer is what the user actually thinks of as "the project" — Project itself, its tasks, its resources, its dependencies, its calendar, its baselines. The service layer is two coordinator classes (ProjectService and ValidationService) that perform operations across multiple domain objects. This split matters because it shows I'm thinking about responsibilities, not just data. A typical "wrong" version of this diagram would shove every method onto Project and end up with a god-object.



Project is the root. It owns its tasks through composition (the filled diamond — tasks die with the project) and uses its resources through aggregation (the open diamond — resources can outlive the project). The distinction between composition and aggregation is one of the things professors love to test, so it's worth being able to defend cleanly. Tasks are composed because they only exist within a project context — a task without a project doesn't make sense, and deleting a project deletes its tasks. Resources are aggregated because in real life a person or a piece of equipment exists in your organization regardless of which project they're assigned to. If you delete a project, the resources don't disappear; they just stop being used by that project.



Project also owns Baselines (composition again — a baseline is a snapshot of a particular project, useless on its own) and uses one Calendar (a one-to-one association — every project has exactly one working calendar).



Task has its own life. Each task can have multiple predecessors and multiple successors through the Dependency class. The "predecessor" and "successor" labels on the lines tell you which end is which. A Dependency object has a type (Finish-to-Start, Start-to-Start, Finish-to-Finish, or Start-to-Finish — the standard four in any project tool) and a lag (a delay between predecessor finish and successor start). Modeling Dependency as its own class rather than a simple link lets it carry data; if it were just a line, there'd be nowhere to put the type and the lag.



Two subclasses inherit from Task: Milestone and SummaryTask. Both demonstrate inheritance. Milestone is a Task whose duration is always zero — it's a marker for an important point in the project. SummaryTask is a Task that contains other tasks (subtasks); its duration and progress are rolled up from its children. The fact that both can be treated polymorphically as Task means the rest of the code can iterate over a list of `Task` objects and the right behavior happens for each subtype. That's polymorphism in action.



Resource is abstract — the italic class name is the visual cue. It can't be instantiated directly. You can't have a Resource that isn't one of HumanResource, MaterialResource, or CostResource. The abstract method `getAvailability(date)` has different implementations in each subclass: a HumanResource's availability depends on their personal calendar and existing assignments, a MaterialResource's depends on stock on hand, a CostResource is always "available" because it represents money rather than a constrained thing. This is textbook polymorphism — same method signature, different behavior depending on the concrete type.



The Assignment class is the most interesting design decision in the diagram. The relationship between Task and Resource is many-to-many: a task can have multiple resources working on it, and a resource can work on multiple tasks. But the relationship has its own data — how many units of the resource are assigned, how many hours of work, how much actual work has been completed, the cost. That data doesn't belong to the Task and it doesn't belong to the Resource — it belongs to the \*pairing\*. The UML way to model this is an association class, a class hanging off the association line by a dashed connector. If a professor asks "why is Assignment connected with a dashed line and not a solid one," that's the answer — it's a notation that specifically means "this class describes the association, it isn't a regular class with a regular relationship."



The two service classes have dashed arrows pointing to Project, meaning they depend on Project (use it as a parameter or call its methods) but don't own it. Dependency is the weakest relationship in UML. It just means "knows about, uses temporarily."



The four OOP principles are all present. \*Encapsulation\* is shown by every attribute being private (the minus sign), with access only through methods. \*Inheritance\* is shown twice — Task → Milestone/SummaryTask, and Resource → HumanResource/MaterialResource/CostResource. \*Polymorphism\* is shown by `getAvailability()` and `verify()` having different behavior across subclasses. \*Abstraction\* is shown by Resource being abstract, hiding the concept of "a thing that can be assigned" from the concrete details of what kind of thing it is.



If the professor asks why I didn't make Task abstract, the answer is that a plain Task is a perfectly valid concept — most tasks aren't milestones or summary tasks, they're just regular tasks. Resource is abstract because there's no such thing as a "generic resource" in the real world; every resource is specifically of some kind.



If they ask why ProjectService and ValidationService aren't combined into one class, the answer is separation of concerns. ProjectService handles lifecycle operations (create, save, export). ValidationService handles checks (overallocation, dependency cycles, schedule consistency). Mixing them would violate the single-responsibility principle and make both classes bigger than they need to be.



\## Activity Diagram — The Workflow of Building a Plan



The activity diagram shows the workflow of creating a project plan from start to finish. It's like a flowchart but with proper UML semantics, especially around concurrency.



The flow starts at the filled black circle and immediately runs Authenticate. Nothing else can start until the user is signed in. Then comes Create Project — entering the project's name, dates, and calendar. Up to this point everything is sequential.



Then comes the fork — the thick black bar with one arrow in and two out. The fork splits the flow into two parallel branches: adding tasks and adding resources. The crucial point about a fork is that both branches genuinely run in parallel; control doesn't pick one over the other. In the real world, a project manager filling in MS Project might enter a few tasks, then a few resources, then more tasks — they don't have to finish all tasks before starting resources. Modeling this with a fork rather than a sequence is more honest about how the system is actually used.



Each branch is itself a loop. The task-loop reads "enter task name, duration, priority; set dependencies if any; check 'more tasks?' — if yes, loop back, if no, exit." The resource-loop is symmetric: "choose type (human, material, or cost); enter cost, max units, calendar; check 'more resources?' — yes loops, no exits."



The two branches converge at the join, another thick black bar, this time with two arrows in and one out. The semantic of a join is that flow doesn't continue past the bar until \*both\* incoming branches have arrived. So Define Milestones doesn't start until you've finished adding both tasks and resources. The fork-and-join pair is what makes the parallelism well-formed; a fork without a matching join would be a modeling error.



After Define Milestones comes the assignment loop, which is the most procedurally interesting part of the whole diagram. For each task that needs a resource, the user picks the task, picks a resource, and the system asks "is this resource available at the required level?" If yes, the assignment is saved. If no, the user goes through "Update or Add Resource" — they can bump the resource's max units, switch to a different resource, or create a new one — and then the loop tries again. After each iteration the system asks "are there unassigned tasks left?" If yes, back to picking a task; if no, exit.



I built the inner availability decision into the assignment loop on purpose, not as an afterthought. The lab description specifically asks for "the addition of resources, their level, and determining the resources needed for the execution of all the project's tasks." The level (max units) of a resource is the key property that determines whether an assignment is feasible. A junior developer with 100% allocation already on Project A can't be put at 100% on Project B in the same week — their level is exhausted. Modeling this check as a real decision point in the workflow shows that the diagram isn't just a happy-path script.



After the assignment loop, the plan goes through validation. Validation checks for things like circular dependencies, overallocations the user missed, tasks without resources, schedule conflicts. If validation fails, the user sees the errors, fixes them, and validates again — a tight retry loop. Only when validation passes does the system calculate the critical path (the longest chain of dependent tasks, which determines the project's overall duration), save the plan to the database, and offer an optional export.



The shapes here are mostly rounded rectangles for actions, hexagons for decisions (PlantUML's rendering choice; they could equally be drawn as diamonds), thick bars for fork and join, and the start/end circles. There are no swimlanes in my version. Swimlanes would be a horizontal or vertical division of the diagram into "lanes" — one per role or component — to show who's responsible for each action. Adding swimlanes (Manager / System / Database) would be a natural enhancement, but the diagram is readable without them. If the professor pushes me on it, I can either defend the simpler version or note that swimlanes would be a good extension.



A common professor question on activity diagrams is "could two of these actions actually happen in parallel? Why or why not?" My answer for the fork: yes, adding tasks and adding resources are independent — there's no data dependency between them. Either can be done first or both at once. After the join, everything is sequential because each step depends on the one before — you can't validate before assigning, can't calculate critical path before validating, can't save before calculating.



\## Sequence Diagram — The Conversation Between Objects



The sequence diagram shows the runtime interaction — which object calls which method on which other object, and in what order. Time flows downward. The participants from left to right are Project Manager (the user), UI, four backend services (TaskService, ResourceService, AssignmentService, ValidationService), and DB.



Splitting the backend into four services rather than one big controller is a design decision worth defending. A single ProjectService class would be simpler to draw but would also be a god-class with too many responsibilities. Having dedicated services for tasks, resources, assignments, and validation matches the actual domain — these are four distinct concerns, each with its own set of operations. It also makes the diagram easier to read: when a message goes to ResourceService, you immediately know it's about resources, not tasks.



The first interaction is project creation. The user calls `createProject` on the UI; the UI delegates to TaskService (in a more polished version this would arguably be a ProjectService, but the principle is the same); the service saves to the DB and gets back a `projectId`; the response propagates back up. This is the standard layered-architecture pattern: UI doesn't talk to the database directly, it goes through a service.



The next two blocks are loops — `loop \[for each task]` and `loop \[for each resource]`. The loop frame around the messages says "everything inside repeats." The guard `\[for each task]` is the loop condition. Each iteration is a complete round-trip: user asks the UI to add something, the UI calls the right service, the service persists to the DB, the DB returns an ID, and the UI confirms back to the user. The reason there are \*two\* separate loops rather than one combined block is that adding a task and adding a resource are different operations going to different services. Drawing them as one loop would be wrong.



The assignment loop is the most complex part of the diagram. For each assignment, the user calls `assignResource(taskId, resId, units)` on the UI. The UI calls AssignmentService.assign. Before saving anything, AssignmentService delegates a check to ValidationService — `checkAvailability(resId, range)`. ValidationService queries the DB for the resource's current usage, computes whether the new assignment fits within the resource's max units for that time range, and returns a result. Now the alt fragment kicks in. The `alt \[available]` branch saves the assignment to the DB and confirms success up to the user. The `\[overallocated]` branch returns a conflict warning to the UI, which displays a warning and a suggestion to the user — without ever saving.



The reason validation happens \*before\* the save, rather than after, is data integrity. If we saved first and validated second, an overallocated assignment would briefly exist in the database, and another concurrent operation could read it as valid. Validating first means the database only ever sees correct data. This is a good thing to mention if the professor asks about transaction handling.



The last block is `opt \[validate full plan]`. The opt fragment means this whole interaction is optional — it runs as a unit or doesn't run at all. In this case, the user can choose to run a plan-wide validation at any point; the UI calls ValidationService.validate, which loads the full project from the DB, runs all the validation checks, and returns a report.



If the professor asks why I didn't use asynchronous messages (which would be drawn with open arrowheads on solid lines), the answer is that nothing in this flow is genuinely fire-and-forget — every message expects a response. Async would be appropriate for something like "send notification email" where the caller doesn't need to wait for delivery, but that's not part of the assignment flow this diagram covers.



If they ask why authentication isn't shown, it's because the sequence diagram is scoped to "adding tasks and resources and saving them," not the full system. Authentication is shown in the use case and activity diagrams; the sequence diagram zooms in on a specific scenario that assumes the user is already logged in.



\## How the Four Diagrams Fit Together



A reviewer expects internal consistency across the four diagrams, and being able to talk about how they relate is part of the defense.



The actors in the use case diagram (Project Manager, Team Member, etc.) correspond to the actor in the sequence diagram (Project Manager). The use cases like Add Task, Add Resource, and Assign Resource to Task have direct counterparts in the activity diagram (the Add Tasks loop, the Add Resources loop, the assignment loop) and in the sequence diagram (the loop fragments). The classes in the class diagram — Project, Task, Resource, Assignment, and so on — are the things being created and saved in the sequence diagram, and the things being manipulated as the activity diagram's flow progresses.



There's one inconsistency worth being upfront about: the class diagram shows two service classes (ProjectService and ValidationService), while the sequence diagram shows four (TaskService, ResourceService, AssignmentService, ValidationService). If the professor catches this, the right answer is "you're correct — for full consistency the class diagram should be expanded to include TaskService, ResourceService, and AssignmentService, since they're real classes the sequence diagram relies on." Acknowledging this kind of thing is much stronger than trying to talk around it.



\## Likely Defense Questions and How to Answer Them



These are the questions a professor is most likely to ask. Having an answer ready makes the defense much smoother.



\*\*Why use a use case diagram rather than just a list of features?\*\* Because a use case diagram captures who interacts with the system, not just what it does. The actor relationships and the include/extend dependencies carry information a flat list can't.



\*\*What's the difference between «include» and «extend», and which way does the arrow point?\*\* Include is mandatory — the source always invokes the target. Extend is conditional — the source enriches the target only when some guard holds. For include, the arrow points from the host \*to\* the included use case (the host knows about the inclusion). For extend, the arrow points from the extension \*to\* the host (the extension knows about the host, but the host doesn't know it's being extended).



\*\*Why is Assignment an association class and not a regular class?\*\* Because the data on Assignment (units, work, actual work, cost) describes the \*relationship\* between a Task and a Resource, not either of them individually. An association class is the standard UML way to attach data to a relationship. A regular class with two foreign keys would technically work but loses the semantic that Assignment can't exist without both endpoints.



\*\*Why is Resource abstract?\*\* Because there's no such thing as a generic resource in real project management. Every resource is either human, material, or cost. Making the base class abstract enforces this in the type system — you can't accidentally create a Resource that isn't one of the three concrete kinds.



\*\*What's the difference between composition and aggregation, and why use each here?\*\* Composition is "owns and dies with" — the parts can't outlive the whole. Aggregation is "uses but doesn't own" — the parts can exist independently. Project–Task is composition because tasks have no meaning outside their project; deleting the project deletes the tasks. Project–Resource is aggregation because a person or a piece of equipment exists in the company regardless of any one project; deleting the project just stops the resources from being used in it.



\*\*Why fork instead of sequence in the activity diagram?\*\* Because adding tasks and adding resources are genuinely independent — there's no data dependency between them. Forcing a sequential order in the model would misrepresent how the system is actually used.



\*\*Why does validation happen before the database save in the sequence diagram?\*\* For data integrity. Saving first and validating second would let invalid data exist briefly in the database, which is a correctness problem in any concurrent system. Validating first ensures the database only ever sees correct data.



\*\*Which OOP principles did you demonstrate, and where?\*\* Encapsulation through private attributes and public methods on every class. Inheritance through Task → Milestone/SummaryTask and Resource → HumanResource/MaterialResource/CostResource. Polymorphism through `getAvailability()` and `verify()` being overridden in subclasses. Abstraction through Resource being abstract.



\*\*What if you were asked to add a new feature, like multi-currency cost reporting?\*\* I'd add a Currency class, a relationship from CostResource and Assignment to Currency, and probably a CurrencyService for conversion logic. The cleanest approach to extending the model is to think of new functionality as new classes with their own relationships, rather than shoving extra fields into existing classes. That keeps the design open to extension and closed to modification.



\*\*Could the four diagrams be more consistent?\*\* Yes — the class diagram should ideally include TaskService, ResourceService, and AssignmentService to match the sequence diagram. If I were polishing the work for a real-world handoff, that's the first thing I'd fix.



\## Final Word



Use case answers "who does what." Class answers "what types exist and how do they relate." Activity answers "in what order do things happen." Sequence answers "who calls whom, and when." Every choice on every diagram should be justifiable in terms of that diagram's purpose. If a professor asks "why is X here," a good answer always boils down to "because it shows something the diagram is supposed to show." If I can't articulate that for some element, it probably shouldn't be there.

