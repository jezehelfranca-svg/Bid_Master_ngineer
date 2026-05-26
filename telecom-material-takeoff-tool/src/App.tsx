/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export default function App() {
  return (
    <div className="w-screen h-screen overflow-hidden bg-[#0b0f19] flex flex-col m-0 p-0">
      <iframe 
        src="/takeoff_tool.html" 
        className="w-full h-full border-none flex-grow" 
        title="Telecom Material Takeoff Tool"
      />
    </div>
  );
}
