from flask import Flask, render_template, request
from hplc_engine.calculations import analyse_peak_data, round_or_blank
from hplc_engine.rules_master import fire_master_rule
from hplc_engine.lever_tracker import determine_lever_state

app = Flask(__name__)
app.secret_key = "replace-this-with-a-real-secret-key"


@app.template_filter("round_blank")
def round_blank_filter(value, digits=3):
    return round_or_blank(value, digits)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyse", methods=["GET", "POST"])
def analyse():
    if request.method == "POST":
        analysis = analyse_peak_data(request.form.to_dict())

        rule = fire_master_rule(analysis["key_data"]["composite_key"])

        lever = determine_lever_state(
            tried_retention=request.form.get("tried_retention") == "on",
            tried_selectivity=request.form.get("tried_selectivity") == "on",
            tried_efficiency=request.form.get("tried_efficiency") == "on",
            tried_gradient=request.form.get("tried_gradient") == "on",
        )

        return render_template("results.html", analysis=analysis, rule=rule, lever=lever)

    return render_template("analyse.html")


if __name__ == "__main__":
    app.run(debug=True)
