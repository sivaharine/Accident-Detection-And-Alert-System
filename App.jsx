import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import LiveFootage from "./pages/LiveFootage";
import AccidentFrames from "./pages/AccidentFrames";
import AccidentVideos from "./pages/AccidentVideos";
import DataAnalysis from "./pages/DataAnalysis";
import FileUpload from "./pages/TestPage";

function App() {
  return (
    <Router>
      <div className="flex h-screen bg-gray-100">
        <Sidebar />
        <div className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<FileUpload />} />
            <Route path="/home" element={<Dashboard />} />
            {/* <Route path="/live-footage" element={<LiveFootage />} /> */}
            <Route path="/accident-frames" element={<AccidentFrames />} />
            <Route path="/accident-videos" element={<AccidentVideos />} />
            <Route path="/data-analysis" element={<DataAnalysis />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
