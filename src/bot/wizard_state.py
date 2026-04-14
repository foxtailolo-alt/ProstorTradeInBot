from aiogram.fsm.state import State, StatesGroup


class TradeInWizardStates(StatesGroup):
    selecting_category = State()
    selecting_model = State()
    answering_question = State()
    waiting_contact_name = State()
    waiting_contact_value = State()
    waiting_comment = State()