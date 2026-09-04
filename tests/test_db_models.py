from services.db import init_db, SessionLocal, DATABASE_URL
from services.models_db import User, UserPreferences
from services.preferences import ensure_preferences, row_to_dict


def test_sqlite_init_and_user_prefs():
    assert "sqlite" in DATABASE_URL or "postgresql" in DATABASE_URL
    init_db()
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == "_test_settings_user").first()
        if not u:
            u = User(username="_test_settings_user", email="_test_settings@local", password_hash="x")
            db.add(u)
            db.commit()
            db.refresh(u)
        pref = ensure_preferences(db, u)
        d = row_to_dict(pref)
        assert d["appearance"]["theme_mode"] in ("dark", "light", "system")
    finally:
        db.close()
