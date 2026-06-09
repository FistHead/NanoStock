from flask import Flask, render_template, request, jsonify, abort

from engine import Simulation

app = Flask(__name__)

# симуляции живут в памяти процесса
SIMS = {}


def get_sim(sim_id):
    sim = SIMS.get(sim_id)
    if sim is None:
        abort(404)
    return sim


# страницы
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/simulations")
def simulations():
    return render_template("simulations.html")


@app.route("/sim/<sim_id>")
def simulation_page(sim_id):
    sim = get_sim(sim_id)
    return render_template("simulation.html", sim_id=sim.id, sim_name=sim.name)


# апи для списка симуляций
@app.get("/api/sims")
def api_sims():
    return jsonify([s.meta() for s in SIMS.values()])


@app.post("/api/sims")
def api_create_sim():
    name = (request.json or {}).get("name", "").strip() or "Новая симуляция"
    sim = Simulation(name)
    SIMS[sim.id] = sim
    return jsonify(sim.meta())


@app.put("/api/sims/<sim_id>")
def api_rename_sim(sim_id):
    sim = get_sim(sim_id)
    sim.name = (request.json or {}).get("name", sim.name).strip() or sim.name
    return jsonify(sim.meta())


@app.delete("/api/sims/<sim_id>")
def api_delete_sim(sim_id):
    SIMS.pop(sim_id, None)
    return jsonify({"ok": True})


# апи для содержимого
@app.get("/api/sims/<sim_id>/state")
def api_state(sim_id):
    return jsonify(get_sim(sim_id).snapshot())


@app.post("/api/sims/<sim_id>/stocks")
def api_add_stock(sim_id):
    sim = get_sim(sim_id)
    d = request.json or {}
    if d.get("random"):
        ok = sim.add_random_stock()
    else:
        ok = sim.add_stock(d.get("name", "акция"), d.get("count", 1000), d.get("invested", 4000))
    return jsonify({"ok": ok, "state": sim.snapshot()})


@app.post("/api/sims/<sim_id>/miples")
def api_add_miple(sim_id):
    sim = get_sim(sim_id)
    d = request.json or {}
    if d.get("random"):
        sim.add_random_miple(d.get("model"))
    else:
        sim.add_miple(d.get("name", "Мипл"), d.get("model", "mrplip_17M_3"),
                      d.get("traits", []), d.get("expr", "happy"))
    return jsonify({"ok": True, "state": sim.snapshot()})


@app.delete("/api/sims/<sim_id>/miples/<mid>")
def api_remove_miple(sim_id, mid):
    sim = get_sim(sim_id)
    sim.remove_miple(mid)
    return jsonify({"ok": True, "state": sim.snapshot()})


@app.post("/api/sims/<sim_id>/auto")
def api_auto(sim_id):
    sim = get_sim(sim_id)
    d = request.json or {}
    sim.autofill(int(d.get("stocks", 4)), int(d.get("miples", 4)), d.get("model"))
    return jsonify({"ok": True, "state": sim.snapshot()})


@app.post("/api/sims/<sim_id>/step")
def api_step(sim_id):
    sim = get_sim(sim_id)
    n = int((request.json or {}).get("steps", 1))
    last = None
    for _ in range(max(1, min(n, 25))):
        last = sim.step()
    return jsonify(last or sim.snapshot())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
