
from flask import Flask, render_template, request, redirect, jsonify
import json
import os
import random

app = Flask(__name__)

DATA_FILE = 'data.json'
PARTICIPANT_FILE = 'participants.json'
CLIENT_FILE = 'clients.json'
GROUP_MAP_FILE = 'group_map.json'

# -------------------- JSON UTILS -----------------------
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -------------------- LOADERS -------------------------
def load_data(): return load_json(DATA_FILE, {})
def save_data(data): save_json(DATA_FILE, data)
def load_participants(): return load_json(PARTICIPANT_FILE, [])
def save_participants(p): save_json(PARTICIPANT_FILE, p)
def load_clients(): return load_json(CLIENT_FILE, [])
def save_clients(c): save_json(CLIENT_FILE, c)
def load_group_map(): return load_json(GROUP_MAP_FILE, {})
def save_group_map(m): save_json(GROUP_MAP_FILE, m)

# -------------------- HELPERS -------------------------
def get_used_numbers_for_participant(data, participant):
    used = set()
    for stage in data.values():
        for group in stage.values():
            if participant in group:
                used.add(group[participant])
    return used

def get_random_number(data, group_participants, participant):
    used_by_person = get_used_numbers_for_participant(data, participant)
    used_numbers = set(group_participants.values()) | used_by_person
    all_possible = list(set(range(1, 1000)) - used_numbers)
    random.shuffle(all_possible)
    return all_possible[0] if all_possible else max(used_numbers) + 1

# -------------------- ROUTES --------------------------
@app.route("/")
def index():
    data = load_data()
    return render_template("index.html", data=data)

@app.route("/participants", methods=["GET", "POST"])
def participants():
    if request.method == "POST":
        raw = request.form["participants"]
        people = [p.strip() for p in raw.strip().split("\n") if p.strip()]
        save_participants(people)
        return redirect("/participants")
    return render_template("participants.html", participants=load_participants())

@app.route("/clients", methods=["GET", "POST"])
def clients():
    if request.method == "POST":
        raw = request.form["clients"]
        base = [c.strip() for c in raw.strip().split("\n") if c.strip()]
        save_clients(base)
        return redirect("/clients")
    return render_template("clients.html", clients=load_clients())

@app.route("/search_participants")
def search_participants():
    query = request.args.get("q", "").lower()
    matches = [p for p in load_participants() if query in p.lower()]
    return jsonify(matches)

@app.route("/create_stage", methods=["GET", "POST"])
def create_stage():
    if request.method == "POST":
        stage = request.form["stage"]
        data = load_data()
        if stage not in data:
            data[stage] = {}
            save_data(data)
        return redirect("/")
    return render_template("create_stage.html")

@app.route("/auto_assign", methods=["GET", "POST"])
def auto_assign():
    participants = load_participants()
    group_map = load_group_map()
    if request.method == "POST":
        stage = request.form["stage"]
        num_groups = int(request.form["groups"])
        names = participants

        # Автогенерация имён групп
        group_names = [f"Group {chr(65+i)}" for i in range(num_groups)]

        data = load_data()
        if stage not in data:
            data[stage] = {}

        assigned = {name: group_map.get(name) for name in names}
        unassigned = [n for n in names if not assigned[n]]
        random.shuffle(unassigned)

        for i, name in enumerate(unassigned):
            group = group_names[i % num_groups]
            group_map[name] = group
            assigned[name] = group

        save_group_map(group_map)

        # Сборка групп
        groups = {g: [] for g in group_names}
        for name, group in assigned.items():
            groups[group].append(name)

        for gname, members in groups.items():
            if gname not in data[stage]:
                data[stage][gname] = {}
            for m in members:
                num = get_random_number(data, data[stage][gname], m)
                data[stage][gname][m] = num

        save_data(data)
        return redirect("/")
    return render_template("auto_assign.html", stages=load_data().keys())

@app.route("/manual_assign", methods=["GET", "POST"])
def manual_assign():
    if request.method == "POST":
        stage = request.form["stage"]
        group = request.form["group"]
        selected = request.form.getlist("participants")

        data = load_data()
        if stage not in data:
            data[stage] = {}
        if group not in data[stage]:
            data[stage][group] = {}

        results = []
        for p in selected:
            num = get_random_number(data, data[stage][group], p)
            data[stage][group][p] = num
            results.append((p, num))

        save_data(data)
        return render_template("manual_result.html", results=results, stage=stage, group=group, stages=load_data().keys(), participants=load_participants())
    return render_template("manual_assign.html", stages=load_data().keys(), participants=load_participants())
