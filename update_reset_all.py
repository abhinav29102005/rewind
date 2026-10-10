import sys

path = "src/rewind/web/team_app.py"
with open(path, "r") as f:
    content = f.read()

target = """    @app.post("/api/v1/demo/reset")
    def reset_demo_files_api(user=Depends(require_user)):
        import subprocess
        try:
            subprocess.run('mkdir -p demo && sqlite3 demo/production.db "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE transactions (id INTEGER PRIMARY KEY, amount REAL);" && echo -e "id,name,role\\n1,Alice,Admin\\n2,Bob,User" > demo/important_data.csv && echo -e "{\\n  \\"database_url\\": \\"sqlite:///production.db\\",\\n  \\"secret_key\\": \\"super-secret-key-do-not-leak\\",\\n  \\"debug\\": false\\n}" > demo/config.json', shell=True)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}"""

replacement = """    @app.post("/api/v1/demo/reset")
    def reset_demo_files_api(user=Depends(require_user)):
        import subprocess
        try:
            # 1. Reset standard demo files
            subprocess.run('mkdir -p demo && rm -rf demo/* demo/.* 2>/dev/null', shell=True)
            subprocess.run('sqlite3 demo/production.db "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE transactions (id INTEGER PRIMARY KEY, amount REAL);"', shell=True)
            subprocess.run('echo -e "id,name,role\\n1,Alice,Admin\\n2,Bob,User" > demo/important_data.csv', shell=True)
            subprocess.run('echo -e "{\\n  \\"database_url\\": \\"sqlite:///production.db\\",\\n  \\"secret_key\\": \\"super-secret-key-do-not-leak\\",\\n  \\"debug\\": false\\n}" > demo/config.json', shell=True)
            
            # 2. Add fake AWS credentials inside demo folder
            subprocess.run('mkdir -p demo/.aws && echo -e "[default]\\naws_access_key_id=AKIAIOSFODNN7EXAMPLE\\naws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" > demo/.aws/credentials', shell=True)
            
            # 3. Create a fake Git repository in demo/ with 5 dummy commits so git reset works
            subprocess.run('cd demo && git init && git config user.email "demo@example.com" && git config user.name "Demo User"', shell=True)
            for i in range(1, 7):
                subprocess.run(f'cd demo && echo "Commit {i}" > dummy.txt && git add dummy.txt && git commit -m "Dummy commit {i}"', shell=True)
            
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Success updating reset for all")
else:
    print("Target not found for reset all")

