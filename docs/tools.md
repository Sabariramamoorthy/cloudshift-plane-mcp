# Tool reference

184 tools. Generated from the `@mcp.tool()` registrations in `plane_mcp/tools/` and `cloudshift/tools/`;
each tool's full docstring (arguments, return shape) is what MCP clients see.

Sections marked *(Commercial / newer Plane)* usually return 404 on self-hosted Community Edition.
See [self-hosted-ce.md](self-hosted-ce.md).

## CloudShift reports

| Tool | Description |
|---|---|
| `cloudshift_plane_daily_report` | Daily CloudShift status report (CE-compatible, deterministic metrics) |
| `cloudshift_plane_user_report` | User workload/status report across projects/modules (READ-only) |
| `cloudshift_plane_module_report` | Module report with per-member breakdown (READ-only) |
| `cloudshift_plane_project_report` | Full project report: progress, distributions, blockers, overdue, stale (READ-only) |
| `cloudshift_plane_cycle_report` | Cycle/sprint report with unfinished and carry-forward candidates (READ-only) |
| `cloudshift_plane_workspace_report` | Workspace portfolio report across all active projects (READ-only) |

## CloudShift diagnostics

| Tool | Description |
|---|---|
| `cloudshift_plane_capability_report` | READ-only CE capability snapshot for CloudShift (no mutations) |

## Projects and estimates

| Tool | Description |
|---|---|
| `list_projects` | List projects in a workspace (lite, paginated) |
| `create_project` | Create a new project |
| `retrieve_project` | Retrieve a project by ID |
| `update_project` | Update a project by ID |
| `delete_project` | Delete a project by ID |
| `manage_project_archive` | Archive or unarchive a project |
| `get_project_worklog_summary` | Get work log summary for a project |
| `get_project_members` | List members of a project (filterable, paginated) |
| `update_project_features` | Update features of a project |
| `get_project_estimate` | Get the estimate configuration for a project |
| `list_project_estimate_points` | List all valid estimate points for a project |
| `create_project_estimate` | Create a new estimate for a project |
| `update_project_estimate` | Update the estimate for a project |
| `delete_project_estimate` | Delete the estimate for a project |
| `link_estimate_to_project` | Link an estimate to a project, making it the active estimate system |
| `create_project_estimate_points` | Create estimate points for a project estimate |
| `update_project_estimate_point` | Update a single estimate point |
| `delete_project_estimate_point` | Delete a single estimate point |

## Work items

| Tool | Description |
|---|---|
| `list_work_items` | List work items with optional PQL filtering |
| `count_work_items` | Count work items across the workspace with optional grouping |
| `create_work_item` | Create a new work item |
| `retrieve_work_item` | Retrieve a work item by ID |
| `retrieve_work_item_by_identifier` | Retrieve a work item by its full identifier (project prefix + sequence number) |
| `update_work_item` | Update a work item by ID |
| `delete_work_item` | Delete a work item by ID |
| `manage_work_item_assignee` | Add or remove a single assignee on a work item without replacing the full list |
| `manage_work_item_label` | Add or remove a single label on a work item without replacing the full list |
| `list_archived_work_items` | List archived work items in a project with optional PQL filtering |
| `manage_work_item_archive` | Archive or unarchive a work item |
| `search_work_items` | Search work items by text across a workspace |

## Work item comments

| Tool | Description |
|---|---|
| `list_work_item_comments` | List comments for a work item |
| `retrieve_work_item_comment` | Retrieve a specific comment for a work item |
| `create_work_item_comment` | Create a comment for a work item |
| `update_work_item_comment` | Update a comment for a work item |
| `delete_work_item_comment` | Delete a comment for a work item |

## Work item links

| Tool | Description |
|---|---|
| `list_work_item_links` | List links for a work item |
| `retrieve_work_item_link` | Retrieve a specific link for a work item |
| `create_work_item_link` | Create a link for a work item |
| `update_work_item_link` | Update a link for a work item |
| `delete_work_item_link` | Delete a link for a work item |

## Work item relations

| Tool | Description |
|---|---|
| `list_work_item_relations` | List every relation for a work item |
| `create_work_item_relation` | Relate a work item to one or more targets |
| `remove_work_item_relation` | Remove ONE relation between two work items |

## Work item relation definitions

| Tool | Description |
|---|---|
| `list_work_item_relation_definitions` | List every relation type usable with create_work_item_relation |
| `create_work_item_relation_definition` | Create a new workspace relation definition |
| `update_work_item_relation_definition` | Update an existing workspace relation definition |
| `delete_work_item_relation_definition` | Delete a workspace relation definition |

## Work item activity

| Tool | Description |
|---|---|
| `list_work_item_activities` | List activities for a work item |
| `retrieve_work_item_activity` | Retrieve a specific activity for a work item |

## Work item attachments

| Tool | Description |
|---|---|
| `list_work_item_attachments` | List all attachments for a work item |
| `get_work_item_attachment_download_url` | Get a presigned download URL for a work item attachment |
| `upload_work_item_attachment_from_url` | Fetch a file from a public URL and attach it to a work item |
| `delete_work_item_attachment` | Delete an attachment from a work item |
| `read_work_item_attachment` | Fetch an attachment's content so the LLM can read or analyze it |

## Work logs

| Tool | Description |
|---|---|
| `list_work_logs` | List work logs for a work item |
| `create_work_log` | Create a work log for a work item |
| `update_work_log` | Update a work log for a work item |
| `delete_work_log` | Delete a work log for a work item |

## Cycles

| Tool | Description |
|---|---|
| `list_cycles` | List cycles in a project. Active (non-archived) cycles by default |
| `create_cycle` | Create a new cycle |
| `retrieve_cycle` | Retrieve a cycle by ID |
| `update_cycle` | Update a cycle by ID |
| `delete_cycle` | Delete a cycle by ID |
| `manage_cycle_work_items` | Add or remove work items on a cycle in a single call |
| `list_cycle_work_items` | List work items in a cycle with optional PQL filtering |
| `transfer_cycle_work_items` | Transfer work items from one cycle to another |
| `manage_cycle_archive` | Archive or unarchive a cycle |
| `complete_cycle` | Complete (close) a cycle by setting its end date to today |

## Modules

| Tool | Description |
|---|---|
| `list_modules` | List modules in a project |
| `create_module` | Create a new module |
| `retrieve_module` | Retrieve a module by ID |
| `update_module` | Update a module by ID |
| `delete_module` | Delete a module by ID |
| `manage_module_work_items` | Add or remove work items on a module in a single call |
| `list_module_work_items` | List work items in a module with optional PQL filtering |
| `manage_module_archive` | Archive or unarchive a module |

## Milestones *(Commercial / newer Plane)*

| Tool | Description |
|---|---|
| `list_milestones` | List all milestones in a project |
| `create_milestone` | Create a new milestone |
| `retrieve_milestone` | Retrieve a milestone by ID |
| `update_milestone` | Update a milestone by ID |
| `delete_milestone` | Delete a milestone by ID |
| `manage_milestone_work_items` | Add or remove work items on a milestone in a single call |
| `list_milestone_work_items` | List work items in a milestone |

## States

| Tool | Description |
|---|---|
| `list_states` | List all states in a project |
| `create_state` | Create a new state |
| `retrieve_state` | Retrieve a state by ID |
| `update_state` | Update a state by ID |
| `delete_state` | Delete a state by ID |

## Labels

| Tool | Description |
|---|---|
| `list_labels` | List all labels in a project |
| `create_label` | Create a new label |
| `retrieve_label` | Retrieve a label by ID |
| `update_label` | Update a label by ID |
| `delete_label` | Delete a label by ID |

## Work item types

| Tool | Description |
|---|---|
| `list_work_item_types` | List work item types. Omit project_id for workspace-level types |
| `create_work_item_type` | Create a new work item type |
| `import_work_item_types_to_project` | Bulk-link workspace-level work item types to a project |
| `resolve_work_item_type` | Find a work item type by name for a project, create it if missing, and link it to the project |
| `retrieve_work_item_type` | Retrieve a work item type by ID |
| `update_work_item_type` | Update a work item type by ID |
| `delete_work_item_type` | Delete a work item type by ID |

## Work item custom properties

| Tool | Description |
|---|---|
| `list_work_item_properties` | List custom work item properties |
| `create_work_item_property` | Create a new work item property |
| `retrieve_work_item_property` | Retrieve a work item property by ID |
| `update_work_item_property` | Update a work item property by ID |
| `delete_work_item_property` | Delete a work item property by ID |
| `manage_work_item_type_properties` | Attach or detach properties on a work item type in a single call |
| `list_work_item_property_options` | List options for a work item property |
| `retrieve_work_item_property_option` | Retrieve a single option from a work item property |
| `create_work_item_property_option` | Create an option on a work item property |
| `update_work_item_property_option` | Update an option on a work item property |
| `delete_work_item_property_option` | Delete an option from a work item property |
| `get_work_item_property_value` | Get the value(s) of a custom property on a work item |
| `set_work_item_property_value` | Set (create or update) the value of a custom property on a work item |
| `delete_work_item_property_value` | Delete the value(s) of a custom property on a work item |

## Workspace

| Tool | Description |
|---|---|
| `get_workspace_members` | List members of the current workspace (filterable, paginated) |
| `get_features` | Get feature flags |
| `update_workspace_features` | Update features of the current workspace |

## Users

| Tool | Description |
|---|---|
| `get_me` | Get current user information |

## Pages *(Commercial / newer Plane)*

| Tool | Description |
|---|---|
| `list_pages` | List pages |
| `attach_page_to_work_item` | Link a page to a work item |
| `list_work_item_pages` | List all pages linked to a work item |
| `detach_page_from_work_item` | Remove a page link from a work item |
| `retrieve_page` | Retrieve a page by ID |
| `create_page` | Create a page |

## Plane Query Language (PQL)

| Tool | Description |
|---|---|
| `get_pql_reference` | Return the Plane Query Language (PQL) syntax reference |

## Initiatives *(Commercial / newer Plane)*

| Tool | Description |
|---|---|
| `list_initiatives` | List all initiatives in a workspace |
| `create_initiative` | Create a new initiative in the workspace |
| `retrieve_initiative` | Retrieve an initiative by ID |
| `update_initiative` | Update an initiative by ID |
| `delete_initiative` | Delete an initiative by ID |
| `list_initiative_projects` | List projects linked to an initiative |
| `manage_initiative_projects` | Link or unlink projects of an initiative. Use list_initiative_projects to read |

## Intake *(Commercial / newer Plane)*

| Tool | Description |
|---|---|
| `list_intake_work_items` | List all intake work items in a project |
| `create_intake_work_item` | Create a new intake work item in a project |
| `retrieve_intake_work_item` | Retrieve an intake work item by work item ID |
| `update_intake_work_item` | Update an intake work item, including triage status |
| `delete_intake_work_item` | Delete an intake work item by work item ID |

## Roles *(Commercial / newer Plane)*

| Tool | Description |
|---|---|
| `list_roles` | List role definitions in the workspace |
| `retrieve_role` | Retrieve a role definition by ID |

## Releases *(Commercial / newer Plane)*

| Tool | Description |
|---|---|
| `list_releases` | List releases in the workspace (paginated) |
| `create_release` | Create a release in the workspace. Name must be unique in the workspace |
| `retrieve_release` | Retrieve a release by ID |
| `update_release` | Update a release by ID. Only the fields you pass are changed |
| `delete_release` | Delete a release by ID |
| `get_release_changelog` | Get a release's changelog (one per release) |
| `update_release_changelog` | Update a release's changelog body |
| `list_release_labels` | List release labels (paginated) |
| `create_release_label` | Create a release label in the workspace palette. Name must be unique |
| `update_release_label` | Update a release label in the palette. Only the fields you pass are changed |
| `delete_release_label` | Delete a release label from the workspace palette, detaching it everywhere |
| `manage_release_labels` | Attach or detach existing palette labels on a release. Use list_release_labels |
| `list_release_tags` | List release tags in the workspace (paginated) |
| `create_release_tag` | Create a release tag (version marker). Version must be unique in the workspace |
| `retrieve_release_tag` | Retrieve a release tag by ID |
| `update_release_tag` | Update a release tag by ID. Only the fields you pass are changed |
| `delete_release_tag` | Delete a release tag by ID |
| `list_release_work_items` | List the work items linked to a release (paginated) |
| `manage_release_work_items` | Add or remove work items on a release. Use list_release_work_items to read |

## Customers *(Commercial / newer Plane)*

| Tool | Description |
|---|---|
| `list_customers` | List customers in the workspace (paginated) |
| `create_customer` | Create a customer, or update the existing one it matches (upsert) |
| `retrieve_customer` | Retrieve a customer by ID |
| `update_customer` | Update a customer by ID. Only the fields you pass are changed |
| `delete_customer` | Delete a customer, addressed either by ID or by its external reference |
| `list_customer_properties` | List customer properties (paginated) |
| `create_customer_property` | Create a customer property (a workspace-wide custom field on customers) |
| `retrieve_customer_property` | Retrieve a customer property by ID |
| `update_customer_property` | Update a customer property. Only the fields you pass are changed |
| `delete_customer_property` | Delete a customer property, and every customer's values for it |
| `get_customer_property_values` | Read the custom property values a customer holds |
| `set_customer_property_values` | Set a customer's custom property values, replacing any current ones |
| `list_customer_requests` | List a customer's requests (paginated) |
| `create_customer_request` | Create a request on a customer |
| `retrieve_customer_request` | Retrieve a customer request by ID |
| `update_customer_request` | Update a customer request. Only the fields you pass are changed |
| `delete_customer_request` | Delete a customer request, and unlink the work items linked through it |
| `list_customer_work_items` | List the work items linked to a customer. Returns all of them, unpaginated |
| `manage_customer_work_items` | Link or unlink work items on a customer. Use list_customer_work_items to read |
