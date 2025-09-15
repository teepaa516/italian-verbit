
import streamlit as st
import json, random, unicodedata
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

st.set_page_config(page_title="Italiano: epäsäännölliset verbit", page_icon="🇮🇹", layout="centered")

DATA_FILE = Path("verbs.json")
PROGRESS_FILE = Path("progress.json")

PERSONS = ["io","tu","lui/lei","noi","voi","loro"]
IMPERATIVE_PERSONS = ["tu","noi","voi"]
TENSES_ALL = ["presente","imperfetto","passato_prossimo","imperativo"]

def normalize(s: str) -> str:
    s = s.strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    return s

@dataclass
class Verb:
    infinitive: str
    translation_fi: str
    present: List[str]
    noi_present: str
    auxiliary: str
    past_participle: str
    imperative: Dict[str,str]
    irregular_imperfect: Optional[List[str]] = None

    @staticmethod
    def from_dict(d: dict) -> "Verb":
        return Verb(
            infinitive=d["infinitive"],
            translation_fi=d.get("translation_fi",""),
            present=d["present"],
            noi_present=d["noi_present"],
            auxiliary=d["auxiliary"],
            past_participle=d["past_participle"],
            imperative=d["imperative"],
            irregular_imperfect=d.get("irregular_imperfect")
        )

    def imperfect(self) -> List[str]:
        if self.irregular_imperfect:
            return self.irregular_imperfect
        if not self.noi_present.endswith("iamo"):
            base = self.noi_present[:-3]
        else:
            base = self.noi_present[:-4]
        endings = ["vo","vi","va","vamo","vate","vano"]
        if self.infinitive == "fare" and self.noi_present.startswith("fac"):
            base = "face"
        if self.infinitive == "dire" and self.noi_present.startswith("dici"):
            base = "dice"
        return [base + e for e in endings]

    def present_for(self, person_idx: int) -> str:
        return self.present[person_idx]

    def imperative_for(self, person_label: str) -> str:
        return self.imperative[person_label]

@dataclass
class Card:
    verb: Verb
    tense: str
    person_idx: Optional[int] = None
    person_label: Optional[str] = None

@dataclass
class Progress:
    boxes: Dict[str, int] = field(default_factory=dict)

    def key(self, c: Card) -> str:
        if c.tense == "imperativo":
            pk = c.person_label
        else:
            pk = PERSONS[c.person_idx]  # type: ignore
        return f"{c.verb.infinitive}|{c.tense}|{pk}"

    def get_box(self, c: Card) -> int:
        return self.boxes.get(self.key(c), 1)

    def update(self, c: Card, correct: bool):
        k = self.key(c)
        cur = self.boxes.get(k, 1)
        if correct:
            self.boxes[k] = min(5, cur + 1)
        else:
            self.boxes[k] = 1

def load_data() -> List[Verb]:
    if not DATA_FILE.exists():
        st.error(f"verbs.json ei löytynyt. Lataa samaan kansioon kuin tämä sovellus.")
        st.stop()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Verb.from_dict(d) for d in data]

def load_progress() -> Progress:
    try:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return Progress(**json.load(f))
    except Exception:
        pass
    return Progress()

def save_progress(p: Progress):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"boxes": p.boxes}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Edistymistä ei voitu tallentaa: {e}")

def make_cards(verbs: List[Verb], tenses: List[str]) -> List[Card]:
    cards = []
    for v in verbs:
        for t in tenses:
            if t == "imperativo":
                for lbl in IMPERATIVE_PERSONS:
                    cards.append(Card(verb=v, tense=t, person_label=lbl))
            else:
                for i in range(6):
                    cards.append(Card(verb=v, tense=t, person_idx=i))
    return cards

def expected_form(card: Card) -> str:
    v = card.verb
    if card.tense == "presente":
        return v.present_for(card.person_idx)  # type: ignore
    if card.tense == "imperfetto":
        return v.imperfect()[card.person_idx]  # type: ignore
    if card.tense == "passato_prossimo":
        aux = "sono" if v.auxiliary == "essere" else "ho"
        io = aux + " " + v.past_participle
        forms = [
            io,
            ("sei" if v.auxiliary=="essere" else "hai") + " " + v.past_participle,
            ("è"  if v.auxiliary=="essere" else "ha")  + " " + v.past_participle,
            ("siamo" if v.auxiliary=="essere" else "abbiamo") + " " + v.past_participle,
            ("siete" if v.auxiliary=="essere" else "avete") + " " + v.past_participle,
            ("sono" if v.auxiliary=="essere" else "hanno") + " " + v.past_participle
        ]
        return forms[card.person_idx]  # type: ignore
    if card.tense == "imperativo":
        return v.imperative_for(card.person_label)  # type: ignore
    raise ValueError("tuntematon aikamuoto")

def pick_due_cards(cards: List[Card], prog: Progress, n: int) -> List[Card]:
    weighted = []
    for c in cards:
        box = prog.get_box(c)
        weight = {1:6, 2:4, 3:2, 4:1, 5:1}[box]
        weighted.extend([c]*weight)
    random.shuffle(weighted)
    seen = set()
    out = []
    for c in weighted:
        k = (c.verb.infinitive, c.tense, c.person_idx, c.person_label)
        if k not in seen:
            out.append(c)
            seen.add(k)
        if len(out) >= n:
            break
    return out

# ----- UI -----
st.title("🇮🇹 Italian epäsäännölliset verbit – harjoitukset")
verbs = load_data()

if "progress" not in st.session_state:
    st.session_state.progress = load_progress()

with st.sidebar:
    st.header("Asetukset")
    mode = st.radio("Harjoitustila", ["Kirjoitusharjoitus", "Monivalinta"], horizontal=False)
    chosen_tenses = st.multiselect("Aikamuodot", TENSES_ALL, default=TENSES_ALL)
    n_questions = st.slider("Kierroksen pituus", 5, 30, 12)
    st.caption("Vinkki: voit rajata aikamuotoja esim. pelkkä 'presente' + 'imperativo'.")
    if st.button("Nollaa edistyminen"):
        st.session_state.progress = Progress()
        save_progress(st.session_state.progress)
        st.success("Edistyminen nollattu.")

cards_all = make_cards(verbs, chosen_tenses)
round_cards = pick_due_cards(cards_all, st.session_state.progress, n_questions)

# Session-state init
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "correct_count" not in st.session_state:
    st.session_state.correct_count = 0
if "finished" not in st.session_state:
    st.session_state.finished = False
if "current_set" not in st.session_state:
    st.session_state.current_set = round_cards
if "show_hint" not in st.session_state:
    st.session_state.show_hint = False
# New keys for controlled feedback flow
if "checked" not in st.session_state:
    st.session_state.checked = False
if "was_correct" not in st.session_state:
    st.session_state.was_correct = False
if "last_correct_form" not in st.session_state:
    st.session_state.last_correct_form = ""
# Keys for MC options and choice persistence
if "mc_options" not in st.session_state:
    st.session_state.mc_options = None  # Optional[List[str]]
if "mc_for_idx" not in st.session_state:
    st.session_state.mc_for_idx = None

def restart_round():
    st.session_state.idx = 0
    st.session_state.correct_count = 0
    st.session_state.finished = False
    st.session_state.current_set = pick_due_cards(cards_all, st.session_state.progress, n_questions)
    st.session_state.show_hint = False
    st.session_state.checked = False
    st.session_state.last_correct_form = ""
    st.session_state.mc_options = None
    st.session_state.mc_for_idx = None
    # Remove radio widget state safely (cannot assign None)
    if "mc_choice" in st.session_state:
        st.session_state.pop("mc_choice")
    st.rerun()

def go_next():
    st.session_state.idx += 1
    st.session_state.show_hint = False
    st.session_state.checked = False
    st.session_state.last_correct_form = ""
    st.session_state.mc_options = None
    st.session_state.mc_for_idx = None
    if "mc_choice" in st.session_state:
        st.session_state.pop("mc_choice")
    if st.session_state.idx >= len(st.session_state.current_set):
        st.session_state.finished = True
    st.rerun()

# Restart when settings change
if st.button("Aloita kierros uusilla asetuksilla"):
    restart_round()

if st.session_state.finished:
    st.success(f"Valmis! Oikein {st.session_state.correct_count}/{len(st.session_state.current_set)}.")
    if st.button("Uusi kierros"):
        restart_round()
    st.stop()

if not st.session_state.current_set:
    st.info("Valitse asetuksista aikamuodot ja aloita kierros.")
    st.stop()

card = st.session_state.current_set[st.session_state.idx]

def card_header(c: Card):
    pron = c.person_label if c.tense=="imperativo" else PERSONS[c.person_idx]
    st.subheader(f"{c.verb.infinitive} ({c.verb.translation_fi}) — {c.tense} — {pron}")

card_header(card)

col1, col2 = st.columns([2,1], vertical_alignment="center")
with col2:
    if st.button("Vihje"):
        st.session_state.show_hint = True
with col1:
    if st.session_state.show_hint:
        st.info(f"Apuverbi: {card.verb.auxiliary} • Partisiippi: {card.verb.past_participle}")

correct = expected_form(card)

if mode == "Kirjoitusharjoitus":
    user_input = st.text_input("Kirjoita oikea muoto", key=f"in_{st.session_state.idx}")

    # Feedback view
    if st.session_state.checked:
        if st.session_state.was_correct:
            st.success("✔ Oikein!")
        else:
            st.error(f"✘ Väärin. Oikea muoto: **{st.session_state.last_correct_form}**")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Seuraava"):
                go_next()
        with c2:
            if st.button("Ohita tämäkin"):
                st.session_state.progress.update(card, False)
                save_progress(st.session_state.progress)
                go_next()

    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Tarkista"):
                is_ok = normalize(user_input) == normalize(correct)
                st.session_state.was_correct = is_ok
                st.session_state.last_correct_form = correct
                st.session_state.progress.update(card, is_ok)
                save_progress(st.session_state.progress)
                st.session_state.checked = True
                if is_ok:
                    st.session_state.correct_count += 1
        with c2:
            if st.button("Ohita"):
                st.session_state.progress.update(card, False)
                save_progress(st.session_state.progress)
                go_next()

else:  # Monivalinta
    # Build stable options for the CURRENT card and keep them until we go to next
    if st.session_state.mc_options is None or st.session_state.mc_for_idx != st.session_state.idx:
        options = {correct}
        # collect distractors from the pool of all cards
        pool = []
        for d in cards_all:
            try:
                pool.append(expected_form(d))
            except Exception:
                pass
        random.shuffle(pool)
        for form in pool:
            if len(options) >= 4:
                break
            if normalize(form) != normalize(correct):
                options.add(form)
        opts = list(options)
        random.shuffle(opts)
        st.session_state.mc_options = opts
        st.session_state.mc_for_idx = st.session_state.idx
        if "mc_choice" in st.session_state:
            st.session_state.pop("mc_choice")

    opts = st.session_state.mc_options
    # Do not preselect; let user choose
    choice = st.radio("Valitse oikea muoto", opts, index=None, key="mc_choice")

    if st.session_state.checked:
        if st.session_state.was_correct:
            st.success("✔ Oikein!")
        else:
            st.error(f"✘ Väärin. Oikea vastaus: **{st.session_state.last_correct_form}**")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Seuraava"):
                go_next()
        with c2:
            if st.button("Ohita tämäkin"):
                st.session_state.progress.update(card, False)
                save_progress(st.session_state.progress)
                go_next()

    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Vastaa"):
                if "mc_choice" not in st.session_state or st.session_state.mc_choice is None:
                    st.warning("Valitse jokin vaihtoehto ensin.")
                else:
                    pick = st.session_state.mc_choice
                    is_ok = normalize(pick) == normalize(correct)
                    st.session_state.was_correct = is_ok
                    st.session_state.last_correct_form = correct
                    st.session_state.progress.update(card, is_ok)
                    save_progress(st.session_state.progress)
                    st.session_state.checked = True
                    if is_ok:
                        st.session_state.correct_count += 1
        with c2:
            if st.button("Ohita"):
                st.session_state.progress.update(card, False)
                save_progress(st.session_state.progress)
                go_next()

st.caption("Aksentit voi jättää pois: 'è' ≈ 'e'. Edistyminen tallentuu paikallisesti progress.json -tiedostoon.")
