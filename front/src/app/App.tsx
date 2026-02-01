import { ChatPage } from "@/pages/chat";
import { KnowledgeGraphPage } from "@/pages/knowledge-graph";
import { MultiAgentPage } from "@/pages/multi-agent";
import { NotionChatPage } from "@/pages/notion-chat";
import styled from "@emotion/styled";
import { useState } from "react";
import { GlobalStyleProvider } from "./providers/globalStyleProvider";
import { QueryProvider } from "./providers/queryProvider";

const AppContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
`;

const NavBar = styled.nav`
  display: flex;
  gap: 0;
  background: #1a1a2e;
  border-bottom: 1px solid #2d2d44;
  padding: 0 16px;
`;

const NavTab = styled.button<{ active: boolean }>`
  padding: 12px 24px;
  border: none;
  background: ${(props) => (props.active ? "#2d2d44" : "transparent")};
  color: ${(props) => (props.active ? "#fff" : "#888")};
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 2px solid ${(props) => (props.active ? "#667eea" : "transparent")};

  &:hover {
    background: #2d2d44;
    color: #fff;
  }
`;

const PageContent = styled.div`
  flex: 1;
  overflow: hidden;
`;

type PageType = "clickup" | "notion" | "multi-agent" | "knowledge-graph";

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>("multi-agent");

  return (
    <QueryProvider>
      <GlobalStyleProvider>
        <AppContainer>
          <NavBar>
            <NavTab
              active={currentPage === "multi-agent"}
              onClick={() => setCurrentPage("multi-agent")}
            >
              Multi-Agent (Notion + ClickUp)
            </NavTab>
            <NavTab
              active={currentPage === "clickup"}
              onClick={() => setCurrentPage("clickup")}
            >
              ClickUp Only
            </NavTab>
            <NavTab
              active={currentPage === "notion"}
              onClick={() => setCurrentPage("notion")}
            >
              Notion Only
            </NavTab>
            <NavTab
              active={currentPage === "knowledge-graph"}
              onClick={() => setCurrentPage("knowledge-graph")}
            >
              Knowledge Graph
            </NavTab>
          </NavBar>
          <PageContent>
            {currentPage === "multi-agent" && <MultiAgentPage />}
            {currentPage === "clickup" && <ChatPage />}
            {currentPage === "notion" && <NotionChatPage />}
            {currentPage === "knowledge-graph" && <KnowledgeGraphPage />}
          </PageContent>
        </AppContainer>
      </GlobalStyleProvider>
    </QueryProvider>
  );
}

export default App;
