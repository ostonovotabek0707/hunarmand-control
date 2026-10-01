# Hunarmand Control

Internal workforce planning, attendance, work-time GPS, tasks, visits, reports and audit platform.

## First build
- PostgreSQL database
- FastAPI backend
- Server-authoritative time
- Role/device foundation
- Monthly plans and tasks
- Attendance events
- Work-time GPS sessions/points
- Audit log

## Rule
Official attendance time is always server time, never the phone clock.
GPS collection starts after check-in and stops after check-out. Employee UI does not expose internal GPS route/history.
