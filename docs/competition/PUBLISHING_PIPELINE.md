# Publishing Pipeline

Publication performs validation, checks required review approvals and unresolved blocking comments, records a publication event, and updates the current published revision atomically. Scheduled releases are durable jobs processed by the explicit due-job endpoint. Rollback republishes an eligible historical revision with a recorded audit event.
