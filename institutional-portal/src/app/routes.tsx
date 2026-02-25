import { createBrowserRouter } from "react-router-dom";
import App from "./App";
import Home from "../pages/Home";
import Project from "../pages/Project";
import TestsHub from "../pages/TestsHub";
import OcrDocumentsTest from "../pages/OcrDocumentsTest";
import MlpdrTest from "../pages/MlpdrTest";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Home /> },
      { path: "project", element: <Project /> },
      { path: "tests", element: <TestsHub /> },
      { path: "tests/ocr", element: <OcrDocumentsTest /> },
      { path: "tests/mlpdr", element: <MlpdrTest /> },
    ],
  },
]);
