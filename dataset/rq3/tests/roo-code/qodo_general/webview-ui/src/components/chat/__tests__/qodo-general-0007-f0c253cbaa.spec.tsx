import React from "react"
import { render } from "@/utils/test-utils"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ExtensionStateContextProvider } from "@src/context/ExtensionStateContext"
import { ChatRowContent } from "../ChatRow"

// Mock i18n
vi.mock("react-i18next", () => ({
	useTranslation: () => ({
		t: (key: string) => {
			const translations: Record<string, string> = {
				"chat:slashCommand.wantsToRun": "Roo wants to run slash command:",
				"chat:slashCommand.didRun": "Roo ran slash command:",
			}
			return translations[key] || key
		},
	}),
	Trans: ({ i18nKey, children }: { i18nKey: string; children?: React.ReactNode }) => {
		return <>{children || i18nKey}</>
	},
	initReactI18next: {
		type: "3rdParty",
		init: () => {},
	},
}))

// Mock VSCodeBadge
vi.mock("@vscode/webview-ui-toolkit/react", () => ({
	VSCodeBadge: ({ children, ...props }: { children: React.ReactNode }) => <span {...props}>{children}</span>,
}))

const queryClient = new QueryClient()

const renderChatRowWithProviders = (message: any, isExpanded = false) => {
	return render(
		<ExtensionStateContextProvider>
			<QueryClientProvider client={queryClient}>
				<ChatRowContent
					message={message}
					isExpanded={isExpanded}
					isLast={false}
					isStreaming={false}
					onToggleExpand={mockOnToggleExpand}
					onSuggestionClick={mockOnSuggestionClick}
					onBatchFileResponse={mockOnBatchFileResponse}
					onFollowUpUnmount={mockOnFollowUpUnmount}
					isFollowUpAnswered={false}
				/>
			</QueryClientProvider>
		</ExtensionStateContextProvider>,
	)
}

const mockOnToggleExpand = vi.fn()
const mockOnSuggestionClick = vi.fn()
const mockOnBatchFileResponse = vi.fn()
const mockOnFollowUpUnmount = vi.fn()

describe("ChatRow - runSlashCommand tool", () => {
	beforeEach(() => {
		vi.clearAllMocks()
	})

	it("should display runSlashCommand ask message with command only", () => {
		const message: any = {
			type: "ask",
			ask: "tool",
			ts: Date.now(),
			text: JSON.stringify({
				tool: "runSlashCommand",
				command: "init",
			}),
			partial: false,
		}

		const { getByText } = renderChatRowWithProviders(message)

		expect(getByText("Roo wants to run slash command:")).toBeInTheDocument()
		expect(getByText("/init")).toBeInTheDocument()
	})

	it("should display runSlashCommand ask message with command and args", () => {
		const message: any = {
			type: "ask",
			ask: "tool",
			ts: Date.now(),
			text: JSON.stringify({
				tool: "runSlashCommand",
				command: "test",
				args: "focus on unit tests",
				description: "Run project tests",
				source: "project",
			}),
			partial: false,
		}

		const { getByText } = renderChatRowWithProviders(message, true) // Pass true to expand

		expect(getByText("Roo wants to run slash command:")).toBeInTheDocument()
		expect(getByText("/test")).toBeInTheDocument()
		expect(getByText("Arguments:")).toBeInTheDocument()
		expect(getByText("focus on unit tests")).toBeInTheDocument()
		expect(getByText("Run project tests")).toBeInTheDocument()
		expect(getByText("project")).toBeInTheDocument()
	})

	it("should display runSlashCommand say message", () => {
		const message: any = {
			type: "say",
			say: "tool",
			ts: Date.now(),
			text: JSON.stringify({
				tool: "runSlashCommand",
				command: "deploy",
				source: "global",
			}),
			partial: false,
		}

		const { getByText } = renderChatRowWithProviders(message)

		expect(getByText("Roo ran slash command:")).toBeInTheDocument()
		expect(getByText("/deploy")).toBeInTheDocument()
		expect(getByText("global")).toBeInTheDocument()
	})

 it("should display readCommandOutput with only totalBytes", () => {
   vi.clearAllMocks()
   const message: any = {
     type: "say",
     say: "tool",
     ts: Date.now(),
     text: JSON.stringify({
       tool: "readCommandOutput",
       totalBytes: 512,
     }),
     partial: false,
   }
 
   const { getByText } = renderChatRowWithProviders(message)
 
   expect(getByText("chat:readCommandOutput.title")).toBeInTheDocument()
   // Expect formatted bytes: 512 B
   expect(getByText(/\(512 B\)/)).toBeInTheDocument()
 })


 it("should display readCommandOutput for search with single match", () => {
   vi.clearAllMocks()
   const message: any = {
     type: "say",
     say: "tool",
     ts: Date.now(),
     text: JSON.stringify({
       tool: "readCommandOutput",
       searchPattern: "foo.*",
       matchCount: 1,
     }),
     partial: false,
   }
 
   const { getByText } = renderChatRowWithProviders(message)
 
   // Title comes from i18n. Our mock returns the key when missing.
   expect(getByText("chat:readCommandOutput.title")).toBeInTheDocument()
   // Info text is rendered inside parentheses; use regex to match the constructed info text
   expect(getByText(/\(search: "foo\.\*" • 1 match\)/)).toBeInTheDocument()
 })


 it("should display readCommandOutput byte range info", () => {
   vi.clearAllMocks()
   const message: any = {
     type: "say",
     say: "tool",
     ts: Date.now(),
     text: JSON.stringify({
       tool: "readCommandOutput",
       readStart: 0,
       readEnd: 2048, // 2 KB
       totalBytes: 1048576, // 1 MB
     }),
     partial: false,
   }
 
   const { getByText } = render(
     <ExtensionStateContextProvider>
       <QueryClientProvider client={queryClient}>
         <ChatRowContent
           message={message}
           isExpanded={false}
           isLast={false}
           isStreaming={false}
           onToggleExpand={mockOnToggleExpand}
           onSuggestionClick={mockOnSuggestionClick}
           onBatchFileResponse={mockOnBatchFileResponse}
           onFollowUpUnmount={mockOnFollowUpUnmount}
           isFollowUpAnswered={false}
         />
       </QueryClientProvider>
     </ExtensionStateContextProvider>,
   )
 
   // Title key is displayed (mock returns key when missing)
   expect(getByText("chat:readCommandOutput.title")).toBeInTheDocument()
   // The formatted byte-range string should be present somewhere in the output
   expect(getByText(/0 B - 2.0 KB of 1.0 MB/)).toBeInTheDocument()
 })


 it("should display api_req_started with cost", () => {
   vi.clearAllMocks()
   const message: any = {
     type: "say",
     say: "api_req_started",
     ts: Date.now(),
     text: JSON.stringify({
       cost: 0.1234,
     }),
     partial: false,
   }
 
   const { getByText } = render(
     <ExtensionStateContextProvider>
       <QueryClientProvider client={queryClient}>
         <ChatRowContent
           message={message}
           isExpanded={false}
           isLast={true}
           isStreaming={false}
           onToggleExpand={mockOnToggleExpand}
           onSuggestionClick={mockOnSuggestionClick}
           onBatchFileResponse={mockOnBatchFileResponse}
           onFollowUpUnmount={mockOnFollowUpUnmount}
           isFollowUpAnswered={false}
         />
       </QueryClientProvider>
     </ExtensionStateContextProvider>,
   )
 
   // Money formatted to 4 decimal places is shown
   expect(getByText("$0.1234")).toBeInTheDocument()
 })

})
