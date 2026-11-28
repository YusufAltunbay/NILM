from panel import auth


def test_register_and_login(tmp_path):
    db = tmp_path / "u.db"
    assert auth.create_user("Kamil", "gizli123", 2, db) is None
    user = auth.verify("kamil", "gizli123", db)
    assert user == {"name": "kamil", "house": 2, "bill": None}
    assert auth.verify("kamil", "yanlis", db) is None
    assert auth.verify("yok", "gizli123", db) is None


def test_validation(tmp_path):
    db = tmp_path / "u.db"
    assert auth.create_user("a", "gizli123", 1, db)          # çok kısa ad
    assert auth.create_user("kamil", "123", 1, db)           # kısa parola
    assert auth.create_user("kamil", "gizli123", 1, db) is None
    assert "alınmış" in auth.create_user("KAMIL", "baska123", 1, db)


def test_password_not_stored_plain(tmp_path):
    db = tmp_path / "u.db"
    auth.create_user("kamil", "gizli123", 1, db)
    assert b"gizli123" not in db.read_bytes()


def test_bill_saved_and_migrated(tmp_path):
    import sqlite3
    db = tmp_path / "u.db"
    c = sqlite3.connect(db)   # eski şema (bill sütunu yok)
    c.execute("CREATE TABLE users(username TEXT PRIMARY KEY, salt TEXT NOT NULL, pw TEXT NOT NULL, house INTEGER NOT NULL)")
    c.commit(); c.close()
    assert auth.create_user("ayse", "parola1", 2, db=db, bill=1300) is None
    assert auth.verify("ayse", "parola1", db=db)["bill"] == 1300
    auth.set_bill("ayse", 0, db=db)
    assert auth.verify("ayse", "parola1", db=db)["bill"] is None


def test_possessive():
    assert auth.possessive("kamil") == "Kamil'in"
    assert auth.possessive("ali") == "Ali'nin"
    assert auth.possessive("murat") == "Murat'ın"
    assert auth.possessive("oğuz") == "Oğuz'un"
    assert auth.possessive("gül") == "Gül'ün"
    assert auth.possessive("ayşe") == "Ayşe'nin"
