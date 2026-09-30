export const UNIFIED_BOUNDARY_GROUP = "unified_boundary";

const SOURCE_SCOPES = ["source"];

const CALL_TRANSPORT = "call";
const CONSTRUCT_TRANSPORT = "new";

const GENERIC_HTTP_ENDPOINT_TRANSPORTS = [
  "fetch",
  "request",
  "axios",
  "got",
  "ky",
].map((callee) => ({
  callee,
  boundary_group: UNIFIED_BOUNDARY_GROUP,
  call_kind: CALL_TRANSPORT,
}));
const GENERIC_WEBSOCKET_ENDPOINT_TRANSPORTS = [
  {
    callee: "WebSocket",
    boundary_group: UNIFIED_BOUNDARY_GROUP,
    call_kind: CONSTRUCT_TRANSPORT,
  },
  {
    callee: "EventSource",
    boundary_group: UNIFIED_BOUNDARY_GROUP,
    call_kind: CONSTRUCT_TRANSPORT,
  },
];

/**
 * Build one reusable TypeScript source boundary rule.
 *
 * Called by: this catalog while constructing SDK and endpoint rules. How it is
 * used downstream: provider certification matches these rules by
 * import/receiver identity or by standard transport plus URL pattern;
 * project-specific wrapper names should not be added here.
 */
function boundaryRule({
  id,
  group = UNIFIED_BOUNDARY_GROUP,
  module = null,
  symbol,
  scopes = SOURCE_SCOPES,
  constraints = null,
  endpointPatterns = [],
  endpointTransports = [],
  artifactEndpoint = false,
  interfaceKind = null,
}) {
  const rule = {
    boundary_id: id,
    boundary_group: group,
    module,
    symbol,
    measurement_scopes: [...scopes],
  };
  if (constraints) rule.call_constraints = constraints;
  if (endpointPatterns.length > 0)
    rule.endpoint_patterns = [...endpointPatterns];
  if (endpointTransports.length > 0) {
    rule.endpoint_transports = endpointTransports.map((transport) => ({
      ...transport,
    }));
  }
  if (artifactEndpoint) rule.artifact_endpoint = true;
  if (interfaceKind) rule.interface_kind = interfaceKind;
  return rule;
}

/**
 * Build a foundational invocation rule for all supported measurement scopes.
 *
 * Called by: official and third-party provider SDK catalog sections. How it is
 * matched: the flow locator requires a real module import/receiver binding plus
 * the configured provider call suffix.
 */
function sourceRule(rule) {
  return boundaryRule({
    ...rule,
    group: UNIFIED_BOUNDARY_GROUP,
    scopes: SOURCE_SCOPES,
  });
}

/** Expand ordered provider rule ids and call suffixes under one module. */
function sdkRules(module, entries) {
  return Object.entries(entries).map(([id, symbol]) =>
    sourceRule({ id, module, symbol }),
  );
}

/**
 * Build a URL-certified standard transport rule.
 *
 * Called by: endpoint catalog sections for fetch/request/WebSocket-style
 * provider calls. How it is matched: the call must use a generic transport and
 * expose a literal/const URL matching one of the provider endpoint patterns.
 */
function endpointRule(rule) {
  return sourceRule({
    ...rule,
    module: null,
    endpointTransports:
      rule.endpointTransports ?? GENERIC_HTTP_ENDPOINT_TRANSPORTS,
  });
}

const OFFICIAL_PROVIDER_SDK_RULES = [
  ...sdkRules("openai", {
    openai_responses_create: "responses.create",
    openai_responses_stream: "responses.stream",
    openai_chat_completions_create: "chat.completions.create",
    openai_chat_completions_stream: "chat.completions.stream",
    openai_beta_chat_completions_parse: "beta.chat.completions.parse",
    openai_beta_chat_completions_stream: "beta.chat.completions.stream",
    openai_embeddings_create: "embeddings.create",
    openai_images_generate: "images.generate",
    openai_audio_speech_create: "audio.speech.create",
    openai_audio_transcriptions_create: "audio.transcriptions.create",
    openai_audio_translations_create: "audio.translations.create",
  }),
  ...sdkRules("@anthropic-ai/sdk", {
    anthropic_messages_create: "messages.create",
    anthropic_messages_stream: "messages.stream",
    anthropic_beta_messages_create: "beta.messages.create",
    anthropic_beta_messages_stream: "beta.messages.stream",
  }),
  ...sdkRules("@google/genai", {
    google_genai_generate_content: "models.generateContent",
    google_genai_generate_content_stream: "models.generateContentStream",
    google_genai_embed_content: "models.embedContent",
    google_genai_batch_embed_contents: "models.batchEmbedContents",
  }),
  ...sdkRules("@google/generative-ai", {
    google_generative_ai_generate_content: ".generateContent",
    google_generative_ai_generate_content_stream: ".generateContentStream",
    google_generative_ai_embed_content: ".embedContent",
    google_generative_ai_batch_embed_contents: ".batchEmbedContents",
  }),
  ...sdkRules("@mistralai/mistralai", {
    mistral_chat_complete: "chat.complete",
    mistral_chat_stream: "chat.stream",
    mistral_embeddings_create: "embeddings.create",
  }),
  ...sdkRules("groq-sdk", {
    groq_chat_completions_create: "chat.completions.create",
  }),
  ...sdkRules("together-ai", {
    together_chat_completions_create: "chat.completions.create",
    together_embeddings_create: "embeddings.create",
    together_images_create: "images.create",
  }),
  ...sdkRules("cohere-ai", {
    cohere_chat: ".chat",
    cohere_generate: ".generate",
    cohere_embed: ".embed",
    cohere_rerank: ".rerank",
  }),
  ...sdkRules("replicate", {
    replicate_run: ".run",
    replicate_stream: ".stream",
  }),
  ...sdkRules("@aws-sdk/client-bedrock-runtime", {
    aws_bedrock_runtime_client_send: ".send",
  }),
  ...sdkRules("@aws-sdk/client-sagemaker-runtime", {
    aws_sagemaker_runtime_client_send: ".send",
  }),
  ...sdkRules("vscode", {
    vscode_language_model_send_request: ".sendRequest",
  }),
];

const COMMON_MODEL_SDK_RULES = [
  ...sdkRules("ai", {
    ai_sdk_generate_text: "generateText",
    ai_sdk_stream_text: "streamText",
    ai_sdk_generate_object: "generateObject",
    ai_sdk_stream_object: "streamObject",
    ai_sdk_embed: "embed",
    ai_sdk_embed_many: "embedMany",
    ai_sdk_generate_image: "generateImage",
    ai_sdk_transcribe: "transcribe",
    ai_sdk_generate_speech: "generateSpeech",
  }),
];

const EXTERNAL_MODEL_ABSTRACTION_RULES = [
  sourceRule({
    id: "node_edge_tts_speech",
    module: "node-edge-tts",
    symbol: ".ttsPromise",
    interfaceKind: "external_model_abstraction",
  }),
  ...sdkRules("@mariozechner/pi-ai", {
    pi_ai_complete: "complete",
    pi_ai_complete_simple: "completeSimple",
    pi_ai_stream_simple: "streamSimple",
    pi_ai_stream_openai_responses: "streamOpenAIResponses",
    pi_ai_stream_anthropic: "streamAnthropic",
    pi_ai_stream_simple_openai_completions: "streamSimpleOpenAICompletions",
  }),
  ...sdkRules("@mariozechner/pi-coding-agent", {
    pi_coding_agent_generate_summary: "generateSummary",
    pi_coding_agent_session_prompt: ".prompt",
  }),
];

const PROVIDER_ENDPOINTS = [
  {
    id: "direct_openai_responses_http",
    symbol: "fetch_openai_responses",
    endpointPatterns: [String.raw`api\.openai\.com\/(?:v1\/)?responses`],
  },
  {
    id: "direct_azure_openai_responses_http",
    symbol: "fetch_azure_openai_responses",
    endpointPatterns: [String.raw`openai\/deployments\/[^/]+\/responses`],
  },
  {
    id: "direct_openai_compatible_responses_http",
    symbol: "fetch_openai_compatible_responses",
    endpointPatterns: [String.raw`(?:\/v1)?\/responses`],
  },
  {
    id: "direct_openai_chat_completions_http",
    symbol: "fetch_openai_chat_completions",
    endpointPatterns: [
      String.raw`api\.openai\.com\/(?:v1\/)?chat\/completions`,
    ],
  },
  {
    id: "direct_azure_openai_chat_completions_http",
    symbol: "fetch_azure_openai_chat_completions",
    endpointPatterns: [
      String.raw`openai\/deployments\/[^/]+\/chat\/completions`,
    ],
  },
  {
    id: "direct_openai_compatible_chat_completions_http",
    symbol: "fetch_openai_compatible_chat_completions",
    endpointPatterns: [String.raw`(?:\/v1)?\/chat\/completions`],
  },
  {
    id: "direct_openai_completions_http",
    symbol: "fetch_openai_completions",
    endpointPatterns: [
      String.raw`(?:api\.openai\.com\/(?:v1\/)?completions|(?:\/v1)?\/completions)`,
    ],
  },
  {
    id: "direct_anthropic_messages_batch_http",
    symbol: "fetch_anthropic_messages_batch",
    endpointPatterns: [
      String.raw`api\.anthropic\.com\/(?:v1\/)?messages\/batches`,
    ],
  },
  {
    id: "direct_anthropic_messages_http",
    symbol: "fetch_anthropic_messages",
    endpointPatterns: [
      String.raw`api\.anthropic\.com\/(?:v1\/)?messages`,
      String.raw`(?:^|https?:\/\/[^/]+)\/v1\/messages(?:[/?#]|$)`,
    ],
  },
  {
    id: "direct_ollama_chat_http",
    symbol: "fetch_ollama_chat",
    endpointPatterns: [String.raw`\/api\/chat`],
  },
  {
    id: "direct_ollama_generate_http",
    symbol: "fetch_ollama_generate",
    endpointPatterns: [String.raw`\/api\/generate`],
  },
  {
    id: "direct_ollama_embed_http",
    symbol: "fetch_ollama_embed",
    endpointPatterns: [String.raw`\/api\/embed(?:[/?#]|$)`],
  },
  {
    id: "direct_google_generate_content_http",
    symbol: "fetch_google_generate_content",
    endpointPatterns: [String.raw`:(?:generateContent|streamGenerateContent)`],
  },
  {
    id: "direct_openai_embeddings_http",
    symbol: "fetch_openai_embeddings",
    endpointPatterns: [String.raw`api\.openai\.com\/(?:v1\/)?embeddings`],
  },
  {
    id: "direct_embedding_provider_http",
    symbol: "embedding_provider_http",
    endpointPatterns: [
      String.raw`(?:\/v1\/embeddings|\/embeddings|\/api\/embeddings|\/v2\/embed|\/v1\/embed|:embedContent|:batchEmbedContents)`,
    ],
  },
  {
    id: "direct_embedding_batch_provider_http",
    symbol: "embedding_batch_provider_http",
    endpointPatterns: [
      String.raw`(?:\/batches|batches\/|:asyncBatchEmbedContent)`,
    ],
  },
  {
    id: "direct_openai_file_content_artifact_http",
    symbol: "fetch_openai_file_content_artifact",
    endpointPatterns: [
      String.raw`(?:api\.openai\.com\/(?:v1\/)?files\/[^/?#]*\/content|(?:\/v1)?\/files\/[^/?#]*\/content)`,
    ],
    artifactEndpoint: true,
  },
  {
    id: "direct_google_file_download_artifact_http",
    symbol: "fetch_google_file_download_artifact",
    endpointPatterns: [
      String.raw`(?:generativelanguage\.googleapis\.com\/.*\/files\/[^/?#:]*:download|files\/[^/?#:]*:download|:download)`,
    ],
    artifactEndpoint: true,
  },
  {
    id: "direct_openai_images_http",
    symbol: "fetch_openai_images_generations",
    endpointPatterns: [
      String.raw`(?:api\.openai\.com\/(?:v1\/)?images\/generations|\/images\/generations)`,
    ],
  },
  {
    id: "direct_openai_audio_speech_http",
    symbol: "fetch_openai_audio_speech",
    endpointPatterns: [
      String.raw`(?:api\.openai\.com\/(?:v1\/)?audio\/speech|\/audio\/speech)`,
    ],
  },
  {
    id: "direct_openai_compatible_audio_transcriptions_http",
    symbol: "fetch_openai_compatible_audio_transcriptions",
    endpointPatterns: [
      String.raw`(?:api\.openai\.com\/(?:v1\/)?audio\/transcriptions|(?:\/v1)?\/audio\/transcriptions)`,
    ],
  },
  {
    id: "direct_openai_compatible_audio_translations_http",
    symbol: "fetch_openai_compatible_audio_translations",
    endpointPatterns: [
      String.raw`(?:api\.openai\.com\/(?:v1\/)?audio\/translations|(?:\/v1)?\/audio\/translations)`,
    ],
  },
  {
    id: "direct_minimax_vlm_http",
    symbol: "fetch_minimax_vlm",
    endpointPatterns: [String.raw`\/v1\/coding_plan\/vlm(?:[/?#]|$)`],
  },
  {
    id: "direct_minimax_image_generation_http",
    symbol: "fetch_minimax_image_generation",
    endpointPatterns: [String.raw`\/v1\/image_generation(?:[/?#]|$)`],
  },
  {
    id: "direct_elevenlabs_text_to_speech_http",
    symbol: "fetch_elevenlabs_text_to_speech",
    endpointPatterns: [String.raw`\/v1\/text-to-speech(?:\/|[?#]|$)`],
  },
  {
    id: "direct_cohere_chat_http",
    symbol: "fetch_cohere_chat",
    endpointPatterns: [String.raw`api\.cohere\.ai\/(?:v1|v2)\/chat`],
  },
  {
    id: "direct_cohere_generate_http",
    symbol: "fetch_cohere_generate",
    endpointPatterns: [String.raw`api\.cohere\.ai\/v1\/generate`],
  },
  {
    id: "direct_cohere_rerank_http",
    symbol: "fetch_cohere_rerank",
    endpointPatterns: [String.raw`api\.cohere\.ai\/(?:v1|v2)\/rerank`],
  },
  {
    id: "direct_bedrock_runtime_invoke_http",
    symbol: "fetch_bedrock_runtime_invoke",
    endpointPatterns: [
      String.raw`bedrock-runtime\.[^/]+\.amazonaws\.com\/model\/[^/]+\/(?:invoke|invoke-with-response-stream|converse|converse-stream)`,
    ],
  },
  {
    id: "direct_openai_realtime_transcription_ws",
    symbol: "websocket_openai_realtime_transcription",
    endpointPatterns: [
      String.raw`wss:\/\/api\.openai\.com\/(?:v1\/)?realtime\?intent=transcription`,
    ],
    endpointTransports: GENERIC_WEBSOCKET_ENDPOINT_TRANSPORTS,
  },
  {
    id: "direct_openai_realtime_ws",
    symbol: "websocket_openai_realtime",
    endpointPatterns: [String.raw`wss:\/\/api\.openai\.com\/(?:v1\/)?realtime`],
    endpointTransports: GENERIC_WEBSOCKET_ENDPOINT_TRANSPORTS,
  },
  {
    id: "direct_openai_responses_ws",
    symbol: "websocket_openai_responses",
    endpointPatterns: [
      String.raw`wss:\/\/api\.openai\.com\/(?:v1\/)?responses`,
    ],
    endpointTransports: GENERIC_WEBSOCKET_ENDPOINT_TRANSPORTS,
  },
];

const DIRECT_PROVIDER_ENDPOINT_RULES = PROVIDER_ENDPOINTS.map((endpoint) =>
  endpointRule(endpoint),
);

export const TYPESCRIPT_ENDPOINT_STRING_HINT_RE = new RegExp(
  [
    String.raw`https?:\/\/`,
    String.raw`wss?:\/\/`,
    String.raw`\/(?:v\d+\/)?(?:chat\/completions|responses|completions|embeddings|images|audio|batches)`,
    String.raw`\/(?:v\d+\/)?api\/(?:chat|generate|embeddings)`,
    String.raw`batches\/`,
    String.raw`\/files\/`,
    String.raw`\/upload`,
    String.raw`:(?:generateContent|streamGenerateContent|embedContent|batchEmbedContents|asyncBatchEmbedContent|download)`,
  ].join("|"),
  "i",
);

/**
 * Return whether a string literal is worth carrying for endpoint source checks.
 *
 * Called by: the TS flow analyzer when recording string facts. This belongs
 * beside endpoint source rules because those strings are not general data-flow
 * facts; they only help certify direct provider transports such as
 * `fetch(url)` or `new WebSocket(url)`.
 */
export function isTypescriptEndpointLikeString(
  text,
  boundaries = TYPESCRIPT_LLM_INVOCATION_BOUNDARIES,
) {
  if (!text) return false;
  if (TYPESCRIPT_ENDPOINT_STRING_HINT_RE.test(text)) return true;
  return (boundaries || []).some((boundary) =>
    (boundary.endpoint_patterns || []).some((pattern) =>
      new RegExp(pattern, "i").test(text),
    ),
  );
}

const RAW_TYPESCRIPT_LLM_INVOCATION_BOUNDARIES = [
  ...OFFICIAL_PROVIDER_SDK_RULES,
  ...COMMON_MODEL_SDK_RULES,
  ...EXTERNAL_MODEL_ABSTRACTION_RULES,
  ...DIRECT_PROVIDER_ENDPOINT_RULES,
];

export const TYPESCRIPT_PROVIDER_CLIENT_CONSTRUCTORS = [
  {
    modules: ["openai"],
    suffixes: ["default", "OpenAI", "AzureOpenAI", "Client"],
  },
  {
    modules: ["@anthropic-ai/sdk"],
    suffixes: ["default", "Anthropic", "Client"],
  },
  {
    modules: ["@google/genai"],
    suffixes: ["default", "GoogleGenAI", "Client"],
  },
  {
    modules: ["@google/generative-ai"],
    suffixes: ["GoogleGenerativeAI", "GenerativeModel"],
  },
  {
    modules: ["@mistralai/mistralai"],
    suffixes: ["Mistral", "MistralClient", "Client"],
  },
  {
    modules: ["groq-sdk"],
    suffixes: ["default", "Groq", "Client"],
  },
  {
    modules: ["together-ai"],
    suffixes: ["default", "Together", "TogetherAI", "Client"],
  },
  {
    modules: ["cohere-ai"],
    suffixes: ["default", "CohereClient", "CohereClientV2", "Client"],
  },
  {
    modules: ["replicate"],
    suffixes: ["default", "Replicate", "ReplicateClient"],
  },
  {
    modules: ["@aws-sdk/client-bedrock-runtime"],
    suffixes: ["BedrockRuntimeClient"],
  },
  {
    modules: ["@aws-sdk/client-sagemaker-runtime"],
    suffixes: ["SageMakerRuntimeClient"],
  },
  {
    modules: ["node-edge-tts"],
    suffixes: ["EdgeTTS"],
  },
  {
    modules: ["vscode"],
    suffixes: ["lm.selectChatModels"],
  },
];

function interfaceKind(boundary) {
  if (boundary.endpoint_patterns?.length) return "direct_provider_http";
  if (boundary.module === "ai") return "common_generation_sdk";
  if (
    boundary.module === "@mariozechner/pi-ai" ||
    boundary.module === "@mariozechner/pi-coding-agent"
  ) {
    return "external_model_abstraction";
  }
  return "official_provider_sdk";
}

function interfaceClass(kind) {
  if (kind === "direct_provider_http" || kind === "official_provider_sdk") {
    return "standard_provider_interface";
  }
  if (
    kind === "common_generation_sdk" ||
    kind === "external_model_abstraction"
  ) {
    return "external_model_abstraction_interface";
  }
  return "unknown_interface";
}

function compileBoundary(boundary) {
  const kind = boundary.interface_kind ?? interfaceKind(boundary);
  return {
    ...boundary,
    ecosystem: "typescript",
    interface_kind: kind,
    interface_class: interfaceClass(kind),
    notes: boundary.description,
    measurement_scopes: boundary.measurement_scopes ?? SOURCE_SCOPES,
  };
}

export const TYPESCRIPT_LLM_INVOCATION_BOUNDARIES =
  RAW_TYPESCRIPT_LLM_INVOCATION_BOUNDARIES.map(compileBoundary);

export function typescriptBoundaries({ measurementScope = null } = {}) {
  let boundaries = TYPESCRIPT_LLM_INVOCATION_BOUNDARIES;
  if (measurementScope !== null) {
    boundaries = boundaries.filter((boundary) =>
      boundary.measurement_scopes.includes(measurementScope),
    );
  }
  return boundaries;
}
