// npx vitest core/webview/__tests__/ClineProvider.apiHandlerRebuild.spec.ts

import * as vscode from "vscode"

import { getModelId } from "@roo-code/types"

import { ContextProxy } from "../../config/ContextProxy"
import { Task, TaskOptions } from "../../task/Task"
import { ClineProvider } from "../ClineProvider"
import { OpenAiCodexOAuthManager, isTokenExpired } from "../../../integrations/openai-codex/oauth"
import { refreshAccessToken } from "../../../integrations/openai-codex/oauth"
import { exchangeCodeForTokens } from "../../../integrations/openai-codex/oauth"
import {
  generateCodeVerifier,
  generateCodeChallenge,
  generateState,
  buildAuthorizationUrl,
  OPENAI_CODEX_OAUTH_CONFIG
} from "../../../integrations/openai-codex/oauth"

// Mock setup
vi.mock("fs/promises", () => ({
	mkdir: vi.fn().mockResolvedValue(undefined),
	writeFile: vi.fn().mockResolvedValue(undefined),
	readFile: vi.fn().mockResolvedValue(""),
	unlink: vi.fn().mockResolvedValue(undefined),
	rmdir: vi.fn().mockResolvedValue(undefined),
}))

vi.mock("../../../utils/storage", () => ({
	getSettingsDirectoryPath: vi.fn().mockResolvedValue("/test/settings/path"),
	getTaskDirectoryPath: vi.fn().mockResolvedValue("/test/task/path"),
	getGlobalStoragePath: vi.fn().mockResolvedValue("/test/storage/path"),
}))

vi.mock("p-wait-for", () => ({
	__esModule: true,
	default: vi.fn().mockResolvedValue(undefined),
}))

vi.mock("delay", () => {
	const delayFn = (_ms: number) => Promise.resolve()
	delayFn.createDelay = () => delayFn
	delayFn.reject = () => Promise.reject(new Error("Delay rejected"))
	delayFn.range = () => Promise.resolve()
	return { default: delayFn }
})

vi.mock("vscode", () => ({
	ExtensionContext: vi.fn(),
	OutputChannel: vi.fn(),
	WebviewView: vi.fn(),
	Uri: {
		joinPath: vi.fn(),
		file: vi.fn(),
	},
	commands: {
		executeCommand: vi.fn().mockResolvedValue(undefined),
	},
	window: {
		showInformationMessage: vi.fn(),
		showWarningMessage: vi.fn(),
		showErrorMessage: vi.fn(),
		onDidChangeActiveTextEditor: vi.fn(() => ({ dispose: vi.fn() })),
	},
	workspace: {
		getConfiguration: vi.fn().mockReturnValue({
			get: vi.fn().mockReturnValue([]),
			update: vi.fn(),
		}),
		onDidChangeConfiguration: vi.fn().mockImplementation(() => ({
			dispose: vi.fn(),
		})),
	},
	env: {
		uriScheme: "vscode",
		language: "en",
		appName: "Visual Studio Code",
	},
	ExtensionMode: {
		Production: 1,
		Development: 2,
		Test: 3,
	},
	version: "1.85.0",
}))

vi.mock("../../../utils/tts", () => ({
	setTtsEnabled: vi.fn(),
	setTtsSpeed: vi.fn(),
}))

vi.mock("../../../api", () => ({
	buildApiHandler: vi.fn(),
}))

vi.mock("../../../integrations/workspace/WorkspaceTracker", () => {
	return {
		default: vi.fn().mockImplementation(() => ({
			initializeFilePaths: vi.fn(),
			dispose: vi.fn(),
		})),
	}
})

vi.mock("../../task/Task", () => ({
	Task: vi.fn().mockImplementation((options) => {
		const mockTask = {
			api: undefined,
			abortTask: vi.fn(),
			handleWebviewAskResponse: vi.fn(),
			clineMessages: [],
			apiConversationHistory: [],
			overwriteClineMessages: vi.fn(),
			overwriteApiConversationHistory: vi.fn(),
			taskId: options?.historyItem?.id || "test-task-id",
			emit: vi.fn(),
			updateApiConfiguration: vi.fn().mockImplementation(function (this: any, newConfig: any) {
				this.apiConfiguration = newConfig
			}),
		}
		// Define apiConfiguration as a property so tests can read it
		Object.defineProperty(mockTask, "apiConfiguration", {
			value: options?.apiConfiguration || { apiProvider: "openrouter", openRouterModelId: "openai/gpt-4" },
			writable: true,
			configurable: true,
		})
		return mockTask
	}),
}))

describe("ClineProvider - API Handler Rebuild Guard", () => {
	let provider: ClineProvider
	let mockContext: vscode.ExtensionContext
	let mockOutputChannel: vscode.OutputChannel
	let mockWebviewView: vscode.WebviewView
	let mockPostMessage: any
	let defaultTaskOptions: TaskOptions
	let buildApiHandlerMock: any

	beforeEach(async () => {
		vi.clearAllMocks()

		const globalState: Record<string, any> = {
			mode: "code",
			currentApiConfigName: "test-config",
		}

		const secrets: Record<string, string | undefined> = {}

		mockContext = {
			extensionPath: "/test/path",
			extensionUri: {} as vscode.Uri,
			globalState: {
				get: vi.fn().mockImplementation((key: string) => globalState[key]),
				update: vi.fn().mockImplementation((key: string, value: any) => (globalState[key] = value)),
				keys: vi.fn().mockImplementation(() => Object.keys(globalState)),
			},
			secrets: {
				get: vi.fn().mockImplementation((key: string) => secrets[key]),
				store: vi.fn().mockImplementation((key: string, value: string | undefined) => (secrets[key] = value)),
				delete: vi.fn().mockImplementation((key: string) => delete secrets[key]),
			},
			workspaceState: {
				get: vi.fn().mockReturnValue(undefined),
				update: vi.fn().mockResolvedValue(undefined),
				keys: vi.fn().mockReturnValue([]),
			},
			subscriptions: [],
			extension: {
				packageJSON: { version: "1.0.0" },
			},
			globalStorageUri: {
				fsPath: "/test/storage/path",
			},
		} as unknown as vscode.ExtensionContext

		mockOutputChannel = {
			appendLine: vi.fn(),
			clear: vi.fn(),
			dispose: vi.fn(),
		} as unknown as vscode.OutputChannel

		mockPostMessage = vi.fn()

		mockWebviewView = {
			webview: {
				postMessage: mockPostMessage,
				html: "",
				options: {},
				onDidReceiveMessage: vi.fn(),
				asWebviewUri: vi.fn(),
			},
			visible: true,
			onDidDispose: vi.fn().mockImplementation((callback) => {
				callback()
				return { dispose: vi.fn() }
			}),
			onDidChangeVisibility: vi.fn().mockImplementation(() => ({ dispose: vi.fn() })),
		} as unknown as vscode.WebviewView

		provider = new ClineProvider(mockContext, mockOutputChannel, "sidebar", new ContextProxy(mockContext))

		// Mock providerSettingsManager
		;(provider as any).providerSettingsManager = {
			saveConfig: vi.fn().mockResolvedValue("test-id"),
			listConfig: vi
				.fn()
				.mockResolvedValue([
					{ name: "test-config", id: "test-id", apiProvider: "openrouter", modelId: "openai/gpt-4" },
				]),
			setModeConfig: vi.fn(),
			activateProfile: vi.fn().mockResolvedValue({
				name: "test-config",
				id: "test-id",
				apiProvider: "openrouter",
				openRouterModelId: "openai/gpt-4",
			}),
			getProfile: vi.fn().mockResolvedValue({
				name: "test-config",
				id: "test-id",
				apiProvider: "openrouter",
				openRouterModelId: "openai/gpt-4",
			}),
		}

		// Get the buildApiHandler mock
		const { buildApiHandler } = await import("../../../api")
		buildApiHandlerMock = vi.mocked(buildApiHandler)

		// Setup default mock implementation
		buildApiHandlerMock.mockReturnValue({
			getModel: vi.fn().mockReturnValue({
				id: "openai/gpt-4",
				info: { contextWindow: 128000 },
			}),
		})

		defaultTaskOptions = {
			provider,
			apiConfiguration: {
				apiProvider: "openrouter",
				openRouterModelId: "openai/gpt-4",
			},
		}

		await provider.resolveWebviewView(mockWebviewView)
	})

	describe("upsertProviderProfile", () => {
		test("calls updateApiConfiguration when provider/model unchanged but profile settings changed (explicit save)", async () => {
			// Create a task with the current config
			const mockTask = new Task({
				...defaultTaskOptions,
				apiConfiguration: {
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				},
			})
			mockTask.api = {
				getModel: vi.fn().mockReturnValue({
					id: "openai/gpt-4",
					info: { contextWindow: 128000 },
				}),
			} as any

			await provider.addClineToStack(mockTask)

			// Save settings with SAME provider and model (simulating Save button click)
			await provider.upsertProviderProfile(
				"test-config",
				{
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
					// Other settings that might change
					rateLimitSeconds: 5,
					modelTemperature: 0.7,
				},
				true,
			)

			// Verify updateApiConfiguration was called because we force rebuild on explicit save/switch
			expect(mockTask.updateApiConfiguration).toHaveBeenCalledWith(
				expect.objectContaining({
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
					rateLimitSeconds: 5,
					modelTemperature: 0.7,
				}),
			)
			// Verify task.apiConfiguration was synchronized
			expect((mockTask as any).apiConfiguration.openRouterModelId).toBe("openai/gpt-4")
			expect((mockTask as any).apiConfiguration.rateLimitSeconds).toBe(5)
			expect((mockTask as any).apiConfiguration.modelTemperature).toBe(0.7)
		})

		test("calls updateApiConfiguration when provider changes", async () => {
			const mockTask = new Task({
				...defaultTaskOptions,
				apiConfiguration: {
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				},
			})
			mockTask.api = {
				getModel: vi.fn().mockReturnValue({
					id: "openai/gpt-4",
					info: { contextWindow: 128000 },
				}),
			} as any

			await provider.addClineToStack(mockTask)

			// Change provider to anthropic
			await provider.upsertProviderProfile(
				"test-config",
				{
					apiProvider: "anthropic",
					apiModelId: "claude-3-5-sonnet-20241022",
				},
				true,
			)

			// Verify updateApiConfiguration was called since provider changed
			expect(mockTask.updateApiConfiguration).toHaveBeenCalledWith(
				expect.objectContaining({
					apiProvider: "anthropic",
					apiModelId: "claude-3-5-sonnet-20241022",
				}),
			)
		})

		test("calls updateApiConfiguration when model changes", async () => {
			const mockTask = new Task({
				...defaultTaskOptions,
				apiConfiguration: {
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				},
			})
			mockTask.api = {
				getModel: vi.fn().mockReturnValue({
					id: "openai/gpt-4",
					info: { contextWindow: 128000 },
				}),
			} as any

			await provider.addClineToStack(mockTask)

			// Change model to different model
			await provider.upsertProviderProfile(
				"test-config",
				{
					apiProvider: "openrouter",
					openRouterModelId: "anthropic/claude-3-5-sonnet-20241022",
				},
				true,
			)

			// Verify updateApiConfiguration was called since model changed
			expect(mockTask.updateApiConfiguration).toHaveBeenCalledWith(
				expect.objectContaining({
					apiProvider: "openrouter",
					openRouterModelId: "anthropic/claude-3-5-sonnet-20241022",
				}),
			)
		})

		test("does nothing when no task is running", async () => {
			// Don't add any task to stack
			buildApiHandlerMock.mockClear()

			await provider.upsertProviderProfile(
				"test-config",
				{
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				},
				true,
			)

			// Should not call buildApiHandler when there's no task
			expect(buildApiHandlerMock).not.toHaveBeenCalled()
		})
	})

	describe("activateProviderProfile", () => {
		test("calls updateApiConfiguration when provider/model unchanged but settings differ (explicit profile switch)", async () => {
			const mockTask = new Task({
				...defaultTaskOptions,
				apiConfiguration: {
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
					modelTemperature: 0.3,
				},
			})
			mockTask.api = {
				getModel: vi.fn().mockReturnValue({
					id: "openai/gpt-4",
					info: { contextWindow: 128000 },
				}),
			} as any

			await provider.addClineToStack(mockTask)

			// Mock activateProfile to return same provider/model but different non-model setting
			;(provider as any).providerSettingsManager.activateProfile = vi.fn().mockResolvedValue({
				name: "test-config",
				id: "test-id",
				apiProvider: "openrouter",
				openRouterModelId: "openai/gpt-4",
				modelTemperature: 0.9,
				rateLimitSeconds: 7,
			})

			await provider.activateProviderProfile({ name: "test-config" })

			// Verify updateApiConfiguration was called due to forced rebuild on explicit switch
			expect(mockTask.updateApiConfiguration).toHaveBeenCalledWith(
				expect.objectContaining({
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				}),
			)
			// Verify task.apiConfiguration was synchronized
			expect((mockTask as any).apiConfiguration.openRouterModelId).toBe("openai/gpt-4")
			expect((mockTask as any).apiConfiguration.modelTemperature).toBe(0.9)
			expect((mockTask as any).apiConfiguration.rateLimitSeconds).toBe(7)
		})

		test("calls updateApiConfiguration when provider changes and syncs task.apiConfiguration", async () => {
			const mockTask = new Task({
				...defaultTaskOptions,
				apiConfiguration: {
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				},
			})
			mockTask.api = {
				getModel: vi.fn().mockReturnValue({
					id: "openai/gpt-4",
					info: { contextWindow: 128000 },
				}),
			} as any

			await provider.addClineToStack(mockTask)

			// Mock activateProfile to return different provider
			;(provider as any).providerSettingsManager.activateProfile = vi.fn().mockResolvedValue({
				name: "anthropic-config",
				id: "anthropic-id",
				apiProvider: "anthropic",
				apiModelId: "claude-3-5-sonnet-20241022",
			})

			await provider.activateProviderProfile({ name: "anthropic-config" })

			// Verify updateApiConfiguration was called
			expect(mockTask.updateApiConfiguration).toHaveBeenCalledWith(
				expect.objectContaining({
					apiProvider: "anthropic",
					apiModelId: "claude-3-5-sonnet-20241022",
				}),
			)
			// And task.apiConfiguration synced
			expect((mockTask as any).apiConfiguration.apiProvider).toBe("anthropic")
			expect((mockTask as any).apiConfiguration.apiModelId).toBe("claude-3-5-sonnet-20241022")
		})

		test("calls updateApiConfiguration when model changes and syncs task.apiConfiguration", async () => {
			const mockTask = new Task({
				...defaultTaskOptions,
				apiConfiguration: {
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				},
			})
			mockTask.api = {
				getModel: vi.fn().mockReturnValue({
					id: "openai/gpt-4",
					info: { contextWindow: 128000 },
				}),
			} as any

			await provider.addClineToStack(mockTask)

			// Mock activateProfile to return different model
			;(provider as any).providerSettingsManager.activateProfile = vi.fn().mockResolvedValue({
				name: "test-config",
				id: "test-id",
				apiProvider: "openrouter",
				openRouterModelId: "anthropic/claude-3-5-sonnet-20241022",
			})

			await provider.activateProviderProfile({ name: "test-config" })

			// Verify updateApiConfiguration was called
			expect(mockTask.updateApiConfiguration).toHaveBeenCalledWith(
				expect.objectContaining({
					apiProvider: "openrouter",
					openRouterModelId: "anthropic/claude-3-5-sonnet-20241022",
				}),
			)
			// And task.apiConfiguration synced
			expect((mockTask as any).apiConfiguration.apiProvider).toBe("openrouter")
			expect((mockTask as any).apiConfiguration.openRouterModelId).toBe("anthropic/claude-3-5-sonnet-20241022")
		})
	})

	describe("profile switching sequence", () => {
		test("A -> B -> A updates task.apiConfiguration each time", async () => {
			const mockTask = new Task({
				...defaultTaskOptions,
				apiConfiguration: {
					apiProvider: "openrouter",
					openRouterModelId: "openai/gpt-4",
				},
			})
			mockTask.api = {
				getModel: vi.fn().mockReturnValue({
					id: "openai/gpt-4",
					info: { contextWindow: 128000 },
				}),
			} as any

			await provider.addClineToStack(mockTask)

			// First switch: A -> B (openrouter -> anthropic)
			;(provider as any).providerSettingsManager.activateProfile = vi.fn().mockResolvedValue({
				name: "anthropic-config",
				id: "anthropic-id",
				apiProvider: "anthropic",
				apiModelId: "claude-3-5-sonnet-20241022",
			})
			await provider.activateProviderProfile({ name: "anthropic-config" })

			expect(mockTask.updateApiConfiguration).toHaveBeenCalled()
			expect((mockTask as any).apiConfiguration.apiProvider).toBe("anthropic")
			expect((mockTask as any).apiConfiguration.apiModelId).toBe("claude-3-5-sonnet-20241022")

			// Second switch: B -> A (anthropic -> openrouter gpt-4)
			;(mockTask.updateApiConfiguration as any).mockClear()
			;(provider as any).providerSettingsManager.activateProfile = vi.fn().mockResolvedValue({
				name: "test-config",
				id: "test-id",
				apiProvider: "openrouter",
				openRouterModelId: "openai/gpt-4",
			})
			await provider.activateProviderProfile({ name: "test-config" })

			// updateApiConfiguration called again, and apiConfiguration must be updated
			expect(mockTask.updateApiConfiguration).toHaveBeenCalled()
			expect((mockTask as any).apiConfiguration.apiProvider).toBe("openrouter")
			expect((mockTask as any).apiConfiguration.openRouterModelId).toBe("openai/gpt-4")
		})
	})

	describe("getModelId helper", () => {
		test("correctly extracts model ID from different provider configurations", () => {
			expect(getModelId({ apiProvider: "openrouter", openRouterModelId: "openai/gpt-4" })).toBe("openai/gpt-4")
			expect(getModelId({ apiProvider: "anthropic", apiModelId: "claude-3-5-sonnet-20241022" })).toBe(
				"claude-3-5-sonnet-20241022",
			)
			expect(getModelId({ apiProvider: "openai", openAiModelId: "gpt-4-turbo" })).toBe("gpt-4-turbo")
			expect(getModelId({ apiProvider: "bedrock", apiModelId: "anthropic.claude-v2" })).toBe(
				"anthropic.claude-v2",
			)
		})

		test("returns undefined when no model ID is present", () => {
			expect(getModelId({ apiProvider: "anthropic" })).toBeUndefined()
			expect(getModelId({})).toBeUndefined()
		})
	})

 test("oauth - exchangeCodeForTokens accountId extraction and missing refresh_token", async () => {
   // Helper to craft fake JWTs (base64url payload)
   const makeJwt = (payloadObj: unknown) => {
     const header = Buffer.from(JSON.stringify({ alg: "none" })).toString("base64url")
     const payload = Buffer.from(JSON.stringify(payloadObj)).toString("base64url")
     return `${header}.${payload}.sig`
   }
 
   // Mock global fetch
   const fetchMock = vi.fn()
 
   // 1) id_token with root-level chatgpt_account_id
   const idTokenRoot = makeJwt({ chatgpt_account_id: "acct-root", email: "root@example.com" })
   fetchMock.mockResolvedValueOnce({
     ok: true,
     status: 200,
     statusText: "OK",
     json: async () => ({
       access_token: "access-1",
       refresh_token: "refresh-1",
       expires_in: 3600,
       id_token: idTokenRoot,
       email: "root@example.com",
     }),
     text: async () => "",
   })
 
   ;(globalThis as any).fetch = fetchMock
 
   const credsRoot = await exchangeCodeForTokens("code-1", "verifier-1")
   expect(credsRoot.type).toBe("openai-codex")
   expect(credsRoot.access_token).toBe("access-1")
   expect(credsRoot.refresh_token).toBe("refresh-1")
   expect(credsRoot.accountId).toBe("acct-root")
   expect(credsRoot.email).toBe("root@example.com")
 
   // 2) id_token with nested claim under https://api.openai.com/auth
   const idTokenNested = makeJwt({ "https://api.openai.com/auth": { chatgpt_account_id: "acct-nested" } })
   fetchMock.mockResolvedValueOnce({
     ok: true,
     status: 200,
     statusText: "OK",
     json: async () => ({
       access_token: "access-2",
       refresh_token: "refresh-2",
       expires_in: 3600,
       id_token: idTokenNested,
     }),
     text: async () => "",
   })
 
   const credsNested = await exchangeCodeForTokens("code-2", "verifier-2")
   expect(credsNested.accountId).toBe("acct-nested")
 
   // 3) access_token used as fallback (no id_token), organizations first id used
   const accessTokenOrg = makeJwt({ organizations: [{ id: "org-1" }, { id: "org-2" }] })
   fetchMock.mockResolvedValueOnce({
     ok: true,
     status: 200,
     statusText: "OK",
     json: async () => ({
       access_token: accessTokenOrg,
       refresh_token: "refresh-3",
       expires_in: 3600,
     }),
     text: async () => "",
   })
 
   const credsOrg = await exchangeCodeForTokens("code-3", "verifier-3")
   expect(credsOrg.accountId).toBe("org-1")
 
   // 4) Missing refresh_token should throw a clear error
   fetchMock.mockResolvedValueOnce({
     ok: true,
     status: 200,
     statusText: "OK",
     json: async () => ({
       access_token: "access-no-refresh",
       expires_in: 3600,
     }),
     text: async () => "",
   })
 
   await expect(exchangeCodeForTokens("code-4", "verifier-4")).rejects.toThrow(
     "Token exchange did not return a refresh_token",
   )
 
   // Cleanup
   ;(globalThis as any).fetch = undefined
 })


 test("oauth - manager save/load/clear and isTokenExpired behavior", async () => {
   const { OpenAiCodexOAuthManager, isTokenExpired } = await import(
     "../../../integrations/openai-codex/oauth"
   )
 
   const manager = new OpenAiCodexOAuthManager()
 
   // saveCredentials should throw when not initialized
   await expect(manager.saveCredentials({} as any)).rejects.toThrow("OAuth manager not initialized")
 
   // Prepare a fake ExtensionContext.secrets store
   const store: Record<string, string | undefined> = {}
   const fakeContext: any = {
     secrets: {
       get: vi.fn(async (k: string) => store[k]),
       store: vi.fn(async (k: string, v: string) => {
         store[k] = v
       }),
       delete: vi.fn(async (k: string) => {
         delete store[k]
       }),
     },
   }
 
   manager.initialize(fakeContext, () => {
     /* swallow logs in tests */
   })
 
   const creds = {
     type: "openai-codex",
     access_token: "access-1",
     refresh_token: "refresh-1",
     expires: Date.now() + 10 * 60 * 1000, // 10 minutes from now
     email: "u@x.com",
   }
 
   // Save credentials (should persist into fake store)
   await manager.saveCredentials(creds)
   expect(fakeContext.secrets.store).toHaveBeenCalled()
 
   // Load credentials back
   const loaded = await manager.loadCredentials()
   expect(loaded?.access_token).toBe("access-1")
   // getCredentials should reflect saved credentials
   expect(manager.getCredentials()?.access_token).toBe("access-1")
 
   // Clear credentials
   await manager.clearCredentials()
   expect(fakeContext.secrets.delete).toHaveBeenCalled()
   expect(manager.getCredentials()).toBeNull()
 
   // Test isTokenExpired buffer behavior:
   const soonExpire = { ...creds, expires: Date.now() + 1 * 60 * 1000 } // 1 minute -> within 5min buffer => expired
   const laterExpire = { ...creds, expires: Date.now() + 10 * 60 * 1000 } // 10 minutes -> not expired
   expect(isTokenExpired(soonExpire as any)).toBe(true)
   expect(isTokenExpired(laterExpire as any)).toBe(false)
 })


 test("oauth - refreshAccessToken parses error response and throws with details", async () => {
   const { refreshAccessToken } = await import("../../../integrations/openai-codex/oauth")
 
   const fetchMock = vi.fn()
   ;(globalThis as any).fetch = fetchMock
 
   // Mock a non-OK response containing structured error JSON
   fetchMock.mockResolvedValueOnce({
     ok: false,
     status: 401,
     statusText: "Unauthorized",
     text: async () =>
       JSON.stringify({
         error: { type: "invalid_grant", message: "token expired" },
         error_description: "detailed description",
       }),
   })
 
   const credentials = {
     type: "openai-codex",
     access_token: "old",
     refresh_token: "refresh-old",
     expires: Date.now() - 1000,
   } as any
 
   try {
     await refreshAccessToken(credentials)
     throw new Error("Expected refreshAccessToken to throw")
   } catch (err: any) {
     // thrown object should include status and parsed errorCode
     expect(err).toBeInstanceOf(Error)
     expect(err.status).toBe(401)
     expect(err.errorCode).toBe("invalid_grant")
     // message should include the parsed description (parseOAuthErrorDetails prefers error_description)
     expect(String(err.message)).toContain("detailed description")
   } finally {
     delete (globalThis as any).fetch
   }
 })


 test("oauth - exchangeCodeForTokens success and missing refresh_token", async () => {
   const { exchangeCodeForTokens } = await import("../../../integrations/openai-codex/oauth")
 
   // Freeze Date.now for deterministic expires calculation
   const nowSpy = vi.spyOn(Date, "now").mockReturnValue(100_000)
 
   const fetchMock = vi.fn()
   ;(globalThis as any).fetch = fetchMock
 
   try {
     // 1) Successful token exchange with refresh_token
     fetchMock.mockResolvedValueOnce({
       ok: true,
       status: 200,
       statusText: "OK",
       json: async () => ({
         access_token: "access-exchange",
         refresh_token: "refresh-exchange",
         expires_in: 3600,
         email: "u@example.com",
       }),
       text: async () => "irrelevant",
     })
 
     const creds = await exchangeCodeForTokens("code-1", "verifier-1")
     expect(creds.type).toBe("openai-codex")
     expect(creds.access_token).toBe("access-exchange")
     expect(creds.refresh_token).toBe("refresh-exchange")
     expect(creds.email).toBe("u@example.com")
     // expires should be based on mocked Date.now
     expect(creds.expires).toBeGreaterThan(Date.now())
 
     // 2) Successful response but missing refresh_token -> should throw specific error
     fetchMock.mockResolvedValueOnce({
       ok: true,
       status: 200,
       statusText: "OK",
       json: async () => ({
         access_token: "access-no-refresh",
         expires_in: 3600,
       }),
       text: async () => "",
     })
 
     await expect(exchangeCodeForTokens("code-2", "verifier-2")).rejects.toThrow(
       "Token exchange did not return a refresh_token",
     )
   } finally {
     // cleanup
     nowSpy.mockRestore()
     delete (globalThis as any).fetch
   }
 })


 test("oauth - PKCE and buildAuthorizationUrl contents", async () => {
   const {
     generateCodeVerifier,
     generateCodeChallenge,
     generateState,
     buildAuthorizationUrl,
     OPENAI_CODEX_OAUTH_CONFIG,
   } = await import("../../../integrations/openai-codex/oauth")
 
   const verifier = generateCodeVerifier()
   // PKCE verifier must exist and be within expected length (43-128 for 32 bytes -> 43 chars)
   expect(typeof verifier).toBe("string")
   expect(verifier.length).toBeGreaterThanOrEqual(43)
   expect(verifier.length).toBeLessThanOrEqual(128)
 
   const challenge = generateCodeChallenge(verifier)
   expect(typeof challenge).toBe("string")
   expect(challenge.length).toBeGreaterThan(0)
   // The challenge method in URL must be S256
   const state = generateState()
   expect(typeof state).toBe("string")
   expect(state.length).toBe(32) // 16 bytes -> 32 hex chars
 
   const authUrl = buildAuthorizationUrl(challenge, state)
   expect(authUrl.startsWith(OPENAI_CODEX_OAUTH_CONFIG.authorizationEndpoint)).toBe(true)
   // Check important params
   expect(authUrl).toContain("code_challenge=")
   expect(authUrl).toContain("code_challenge_method=S256")
   expect(authUrl).toContain(`state=${encodeURIComponent(state)}`)
   // Codex-specific parameters
   expect(authUrl).toContain("codex_cli_simplified_flow=true")
   expect(authUrl).toContain("originator=roo-code")
   // client_id and redirect_uri present
   expect(authUrl).toContain(`client_id=${encodeURIComponent(OPENAI_CODEX_OAUTH_CONFIG.clientId)}`)
   expect(authUrl).toContain(`redirect_uri=${encodeURIComponent(OPENAI_CODEX_OAUTH_CONFIG.redirectUri)}`)
 })

})
