import { useState } from "react";

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!username.trim()) {
      setError("Username is required");
      return;
    }

    try {
      // ako kasnije koristiš backend login:
      // const res = await api.login({ username, password })

      onLogin(username.trim());
    } catch (err) {
      setError("Login failed");
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.card}>
        <h2 style={{ marginBottom: 20 }}>Login</h2>

        <form onSubmit={handleSubmit}>
          <input
            style={styles.input}
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <input
            style={styles.input}
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <p style={{ color: "red" }}>{error}</p>}

          <button style={styles.button} type="submit">
            Login
          </button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    height: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: "#0f172a",
    color: "white",
  },
  card: {
    width: 320,
    padding: 24,
    borderRadius: 12,
    background: "#1e293b",
  },
  input: {
    width: "100%",
    padding: 10,
    marginBottom: 10,
    borderRadius: 6,
    color: "black",
    border: "1px solid #334155",
  },
  button: {
    width: "100%",
    padding: 10,
    borderRadius: 6,
    border: "none",
    background: "#3b82f6",
    color: "white",
    cursor: "pointer",
  },
};