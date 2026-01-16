import os


def create_framework_structure():
    # Glavna lista foldera i fajlova na osnovu tvoje strukture
    structure = [
        "config/environments.yaml",
        "config/secrets.yaml",
        "api/clients/base_client.py",
        "api/clients/policy_client.py",
        "api/clients/auth_client.py",
        "api/schemas/__init__.py",
        "api/tests/__init__.py",
        "ui/pages/base_page.py",
        "ui/pages/login_page.py",
        "ui/pages/policy_page.py",
        "ui/components/__init__.py",
        "ui/tests/test_login.py",
        "testdata/factories/__init__.py",
        "testdata/static/__init__.py",
        "utils/logger.py",
        "utils/waiters.py",
        "utils/assertions.py",
        "fixtures/api_fixtures.py",
        "fixtures/ui_fixtures.py",
        "fixtures/db_fixtures.py",
        "conftest.py",
        "pytest.ini",
        "requirements.txt",
        ".gitignore"
    ]

    for path in structure:
        # Razdvajamo putanju od imena fajla
        directory = os.path.dirname(path)

        # Kreiramo folder ako ne postoji
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Kreiran folder: {directory}")

        # Kreiramo prazan fajl
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                if path.endswith(".py") and "pages" in path:
                    f.write("# Page Object Model Class\n")
                elif "requirements.txt" in path:
                    f.write("pytest\nplaywright\npytest-playwright\nallure-pytest\n")
            print(f"Kreiran fajl: {path}")

    print("\n✅ Struktura frameworka je uspešno kreirana!")


if __name__ == "__main__":
    create_framework_structure()