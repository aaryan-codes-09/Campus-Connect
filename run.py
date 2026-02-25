#!/usr/bin/env python3
"""CampusConnect v2.0 – Quick Start"""
import os, sys
for d in ['instance','static/uploads/events','static/uploads/memories','static/uploads/profiles','static/uploads/qr']:
    os.makedirs(d, exist_ok=True)

from app import app, init_db
init_db()

print("\n" + "━"*55)
print("🎓  CampusConnect v2.0")
print("    ISBM College of Engineering, Pune")
print("━"*55)
print("🌐  Open: http://localhost:5000")
print("━"*55)
print("👤  Admin:     admin@isbm.edu.in      / admin@isbm123")
print("👩‍🏫  Teacher:   teacher@isbm.edu.in   / teacher@123")
print("🎪  Organizer: organizer@isbm.edu.in  / organizer@123")
print("🎓  Student:   Register on the site")
print("━"*55)
print("✨  Features:")
print("    • Role-based Dashboards (Student/Teacher/Organizer/Admin)")
print("    • QR-based Attendance with live tracking")
print("    • Timetable management")  
print("    • Event Memories Gallery (upload/like/download)")
print("    • Notices with WhatsApp share")
print("    • Privacy: students see ONLY their own data")
print("    • Teacher sees student attendance reports")
print("    • Organizer manages events & memories")
print("━"*55 + "\n")

app.run(debug=True, host='0.0.0.0', port=5000)
