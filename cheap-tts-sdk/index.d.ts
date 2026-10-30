export type CheapTtsVoice = {
    id: string;
    name: string;
    language: string;
    useCase: string;
};
export type CheapTtsProgress = {
    stage: "session" | "model" | "synthesis";
    progress: number | null;
};
/** Extra silence inserted at punctuation boundaries, in seconds (0–2).
 *  Omit or leave a field at 0 to keep the model's own pause, which is the
 *  default and the fastest path — a raised value makes the server cut the audio
 *  at that boundary so real silence can follow. */
export type CheapTtsPauses = {
    sentence?: number;
    comma?: number;
    ellipsis?: number;
    paragraph?: number;
};
export type SynthesizeOptions = {
    text: string;
    voice: string;
    rate?: number;
    pauses?: CheapTtsPauses;
    onProgress?: (event: CheapTtsProgress) => void;
};
export type LoadVoiceOptions = {
    voice: string;
    onProgress?: (event: CheapTtsProgress) => void;
    signal?: AbortSignal;
};
export type SynthesisResult = {
    audio: Blob;
    arrayBuffer: ArrayBuffer;
    seconds: number;
    voice: CheapTtsVoice;
};
export type CheapTtsOptions = {
    publishableKey: string;
    apiBase?: string;
    workerUrl?: string;
    vendorBase?: string;
    telemetry?: boolean;
    /** Identifies an official wrapper in operational telemetry. Defaults to browser. */
    runtime?: "browser" | "react";
};
export type CheapTtsErrorCode = "method_not_allowed" | "origin_required" | "invalid_publishable_key_or_origin" | "invalid_server_key" | "invalid_session" | "invalid_credentials" | "subscription_required" | "invalid_content_type" | "request_too_large" | "rate_limited" | "invalid_json" | "text_required" | "text_too_long" | "voice_required" | "unknown_voice" | "invalid_request" | "invalid_telemetry_event" | "invalid_telemetry" | "authentication_unavailable" | "catalog_unavailable" | "session_unavailable" | "prepare_failed";
export declare class CheapTtsApiError extends Error {
    readonly status: number;
    readonly code?: CheapTtsErrorCode;
    readonly requestId?: string;
    constructor(message: string, status: number, code?: CheapTtsErrorCode, requestId?: string);
}
export declare class CheapTts {
    private readonly publishableKey;
    private readonly apiBase;
    private readonly workerUrl;
    private readonly wasmPaths;
    private readonly telemetryEnabled;
    private readonly runtime;
    private session;
    private sessionPromise;
    private worker;
    private workerReady;
    private loadedAsset;
    private jobs;
    private nextJobId;
    private queue;
    private modelQueue;
    constructor(options: CheapTtsOptions);
    voices(): Promise<CheapTtsVoice[]>;
    loadVoice(options: LoadVoiceOptions): Promise<CheapTtsVoice>;
    synthesize(options: SynthesizeOptions): Promise<SynthesisResult>;
    destroy(): void;
    private runSynthesis;
    private tagFailure;
    private isTaggedFailure;
    private telemetryErrorCode;
    private sendTelemetry;
    private ensureSession;
    private prepare;
    private ensureWorker;
    private ensureModel;
    private queueModel;
    private onWorkerMessage;
}
export default CheapTts;
