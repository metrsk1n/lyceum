from aiogram.fsm.state import State, StatesGroup


class TestFlow(StatesGroup):
    answering = State()


class DonationFlow(StatesGroup):
    waiting_amount = State()


class PromoFlow(StatesGroup):
    waiting_code = State()


class AdminFlow(StatesGroup):
    # ── Add Question ──────────────────────────────────────────
    aq_lang = State()
    aq_subject = State()
    aq_text = State()
    aq_options = State()
    aq_correct = State()
    aq_explanation = State()
    aq_difficulty = State()

    # ── Edit Question ─────────────────────────────────────────
    eq_id = State()        # waiting for question ID input
    eq_value = State()     # waiting for new field value

    # ── Delete Question ───────────────────────────────────────
    dq_id = State()        # waiting for question ID input

    # ── Search Questions ──────────────────────────────────────
    sq_query = State()

    # ── Import JSON ───────────────────────────────────────────
    import_wait = State()

    # ── Subjects ──────────────────────────────────────────────
    subj_add_slug = State()
    subj_add_title = State()
    subj_edit_title = State()

    # ── Users ─────────────────────────────────────────────────
    users_search = State()

    # ── Settings ──────────────────────────────────────────────
    set_value = State()

    # ── Broadcast ─────────────────────────────────────────────
    broadcast_waiting = State()
    broadcast_confirm = State()
    promo_waiting = State()
