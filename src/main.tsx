import React from "react";
import ReactDOM from "react-dom/client";
import { RootApp } from "./RootApp";
import "./styles.css";
import "./project-styles.css";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RootApp />
  </React.StrictMode>,
);
