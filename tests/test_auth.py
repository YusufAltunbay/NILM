from panel import auth


def test_register_and_login(tmp_path):
    db = tmp_path / "u.db"
    assert auth.create_user("Kamil", "gizli123", 2, db) is None
    user = auth.verify("kamil", "gizli123", db)
    assert user == {"name": "kamil", "house": 2}
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
