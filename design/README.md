# Database Design
The database design for Task Management System

---

## Database Choise

- **Database Type**: SQL (Postgre)
    - The task data will be structured
    - SQL is fast which will help system performance

---

## ER Diagram: 
Entity-Relation Diagram:
![alt text](<Task Management.png>)

---

## Tables

1. **tasks**:
    - id: bigint [primary key]
    - title: varchar [not null]
    - description: text
    - status: enum [not null]
    - priority: smallint [not null]
    - due_date: timestamp
    - updated_on: timestamp
    - created_at: timestamp
    - created_by: UUID [ref: > users.id]
    - current_assignment_id: bigint

    **Details:**
    - **status**: Following status will be used in enum.
        - unassigned
        - assigned
        - in_progress
        - review
        - complete
        - abandoned

    - **priority**: Priority is integer value ranging from 1 to 5. 1 being lowest and 5 being highest

    - **current_assignment_id**: To which team member task is currently assigned. 

2. **teams**: <br>
    Each user will be assigned to a team. Having seperate teams table helps in retriving team specific data. eg: how many task assigned to team 1 are completed.
    - id: serial [primary key]
    - name: varchar [not null]
    - created_at: timestamp

3. **users**:
    - id: uuid [primary key]
    - username: varchar
    - email: varchar
    - hashed_password: text
    - is_active: bool [not null, default: true]
    - is_superuser: bool [not null, default: false]
    - last_login: timestamp
    - team_id: integer [ref: < teams.id]
    - created_at: timestamp

    **Details**

    - **team_id**: Foreign key from teams. The team to which user is assigned to.

4. **assignment**: <br>
    Users can delegate tasks to other users. In such case we will need to keep track of the delegation, Hence we need seperate assignment table.

    - id: bigint [primary key]
    - task_id: bigint [ref: > tasks.id]
    - assigned_to: uuid [ref: > users.id]
    - assigned_by: uuid [ref: > users.id]
    - assigned_at: timestamp [not null]
    
    **Details**

    - **task_id**: Foreign key from the tasks
    - **assigned_to**: Foreign key from users
    - **assigned_by**: Foreign key from users
    - **delegation**: If task is delegated to another team member then value will be true. Defaults to false.

5. **task_comments**: <br>
    As each task can have multiple comments, we can create new table.
    - id: bigserial [primary key]
    - task_id: bigint [ref: > tasks.id]
    - author_id: uuid
    - body: text [not null]
    - created_at: timestamp [not null]
    - edited_at: timestamp

6. **task_dependencies**: <br>
    Task can be dependant on multiple tasks so seperate table is needed for multivalued properties.
    - task_id: bigint [ref: > tasks.id]
    - depends_on_task_id: bigint [not null]

7. **roles**: 
    - id: serial [primary key]
    - name: varchar [not null, unique]
    - description: text    

8. **permissions**:
    - id: serial [primary key]
    - name: varchar [not null, unique]
    - description: text

9. **user_roles**:
    - user_id: uuid [not null, ref: > users.id]
    - role_id: integer [not null, ref: > roles.id]

10. **role_permissions**:
    - role_id: integer [not null, ref: > roles.id]
    - permission_id: integer [not null, ref: > permissions.id]

11. **refresh_tokens**:
    - id: bigserial [primary key]
    - user_id: uuid [not null, ref: > users.id]
    - jti uuid: [not null]
    - issued_at: timestamp [not null]
    - expires_at: timestamp [not null]
    - revoked: bool [default: false]

12. **user_tokens**:
    - id: bigserial [primary key]
    - user_id: uuid [not null, ref: > users.id]
    - token_hash: text [not null]
    - token_type: varchar [not null]
    - expires_at: timestamp [not null]
    - used: bool [not null, default: false]
    - created_at: timestamp [not null]

13. **auth_events**:
    - id: bigserial [primary key]
    - user_id: uuid [ref: > users.id]
    - event_type: varchar
    - details: text
    - created_at: timestamp [not null]

---

## Indexes
For faster performance we can create index on following columns
1. idx_tasks_status on tasks (status)
2. idx_tasks_priority ON tasks (priority)
3. idx_tasks_duedate ON tasks (due_date)
4. idx_users_team ON users (team_id)
5. idx_assignment_task ON assignment (task_id)
6. idx_assignment_assigned_to ON assignment (assigned_to)
7. idx_comments_task ON task_comments (task_id)

