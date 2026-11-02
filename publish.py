"""Publie sur la fiche Google Business Profile de Klymax les posts du calendrier posts.json.

Lancé chaque jour par GitHub Actions. Publie les posts dont la date (heure de Paris) est atteinte
et qui ne figurent pas encore dans published.json, vérifie ensuite l'état des posts récents.
Le job échoue si un post est refusé par Google, pour déclencher l'alerte e-mail de GitHub.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ACCOUNT = "accounts/110390199561148926648"
LOCATION = "locations/10221904394084913389"
POSTS_URL = f"https://mybusiness.googleapis.com/v4/{ACCOUNT}/{LOCATION}/localPosts"
IMAGE_BASE = "https://klymax.fr/images/"
MAX_PER_RUN = 2
ROOT = Path(__file__).parent
STATE_FILE = ROOT / "published.json"


def access_token() -> str:
    data = urllib.parse.urlencode({
        "client_id": os.environ["GBP_CLIENT_ID"],
        "client_secret": os.environ["GBP_CLIENT_SECRET"],
        "refresh_token": os.environ["GBP_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data) as r:
        return json.load(r)["access_token"]


def api(method: str, url: str, token: str, body=None):
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:2000]


def tracked(url: str, post_id: str) -> str:
    q = urllib.parse.urlencode({"utm_source": "google", "utm_medium": "gbp_post",
                                "utm_campaign": "posts_2026", "utm_content": post_id})
    return f"{url}{'&' if '?' in url else '?'}{q}"


def gdate(d: dt.date) -> dict:
    return {"year": d.year, "month": d.month, "day": d.day}


def build(post: dict) -> dict:
    body = {
        "languageCode": "fr",
        "summary": post["summary"],
        "media": [{"mediaFormat": "PHOTO", "sourceUrl": IMAGE_BASE + post["image"]}],
    }
    link = tracked(post["url"], post["id"])
    if post["type"] == "OFFER":
        start = dt.date.fromisoformat(post["date"])
        end = start + dt.timedelta(days=post.get("offer_days", 21))
        body["topicType"] = "OFFER"
        body["event"] = {"title": post["offer_title"],
                         "schedule": {"startDate": gdate(start), "endDate": gdate(end)}}
        body["offer"] = {"redeemOnlineUrl": link}
    else:
        body["topicType"] = "STANDARD"
        body["callToAction"] = {"actionType": post.get("cta", "LEARN_MORE"), "url": link}
    return body


def main() -> int:
    today = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    only = sys.argv[1] if len(sys.argv) > 1 else None
    posts = json.loads((ROOT / "posts.json").read_text(encoding="utf-8"))
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    token = access_token()

    status, existing = api("GET", POSTS_URL + "?pageSize=100", token)
    if status != 200:
        print("Lecture des posts impossible", status, existing)
        return 1
    live_by_text = {p.get("summary", "").strip(): p for p in existing.get("localPosts", [])}

    due = [p for p in posts if p["id"] not in state and dt.date.fromisoformat(p["date"]) <= today]
    if only:
        due = [p for p in due if p["id"] == only]
    failures = 0
    for post in due[:MAX_PER_RUN]:
        found = live_by_text.get(post["summary"].strip())
        if found:
            print("Déjà en ligne, enregistré sans republier :", post["id"])
            result = found
        else:
            status, result = api("POST", POSTS_URL, token, build(post))
            if status != 200:
                print("Échec de publication", post["id"], status, result)
                failures += 1
                continue
            print("Publié", post["id"], result.get("state"), result.get("searchUrl"))
        state[post["id"]] = {"name": result.get("name"), "state": result.get("state"),
                             "searchUrl": result.get("searchUrl"),
                             "createTime": result.get("createTime"), "planned": post["date"]}

    for pid, rec in state.items():
        if rec.get("state") in (None, "PROCESSING", "LOCAL_POST_STATE_UNSPECIFIED") and rec.get("name"):
            status, cur = api("GET", f"https://mybusiness.googleapis.com/v4/{rec['name']}", token)
            if status == 200:
                rec["state"] = cur.get("state")
                rec["searchUrl"] = cur.get("searchUrl") or rec.get("searchUrl")
        if rec.get("state") == "REJECTED":
            print("Post refusé par Google :", pid)
            failures += 1

    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    remaining = sum(1 for p in posts if p["id"] not in state)
    print(f"{len(state)} publiés, {remaining} restants")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
