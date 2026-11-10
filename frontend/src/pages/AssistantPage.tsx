import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles, ArrowUpRight, Send } from "lucide-react";
import type { AIFinding, ChatProvider, ChatResponse, City, ZoneFeatureCollection, ZoneProperties } from "../types";
import { aiService } from "../services/aiService";
import { Card } from "../components/common/Card";
import { Badge } from "../components/common/Badge";
import { Button } from "../components/common/Button";
import { Notice } from "../components/common/Notice";
import { Pending } from "../components/common/Pending";
import { ZonePicker } from "../components/zone/ZonePicker";
import { ZoneDetails } from "../components/zone/ZoneDetails";
import { interventionNames } from "../lib/constants";
import { fmt } from "../lib/utils";

export interface AssistantPageProps {
  city: City | string;
  data: ZoneFeatureCollection;
  selected: ZoneProperties;
  onSelect: (zone: ZoneProperties) => void;
  navigate?: (page: string) => void;
}

interface MessageItem {
  role: "user" | "assistant";
  text?: string;
  response?: ChatResponse;
}

export function AssistantPage({
  city,
  data,
  selected,
  onSelect,
  navigate,
}: AssistantPageProps) {
  const [message, setMessage] = useState("");
  const [provider, setProvider] = useState<ChatProvider>("auto");
  const [messages, setMessages] = useState<MessageItem[]>([]);

  const send = useMutation<ChatResponse, Error, string>({
    mutationFn: (question: string) =>
      aiService.chat({
        city: city as City,
        zone_id: selected.id,
        message: question,
        provider,
      }),
    onSuccess: (r) =>
      setMessages((m) => [...m, { role: "assistant", response: r }]),
  });

  function submit(q: string) {
    if (!q.trim() || send.isPending) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setMessage("");
    send.mutate(q);
  }

  return (
    <>
      <div className="section-toolbar">
        <ZonePicker data={data} selected={selected} onSelect={onSelect} />
        <select
          className="select"
          aria-label="AI provider"
          value={provider}
          onChange={(e) => setProvider(e.target.value as ChatProvider)}
        >
          <option value="auto">Auto · Groq → Gemini</option>
          <option value="groq">Groq</option>
          <option value="gemini">Gemini</option>
          <option value="local">Local evidence summary</option>
        </select>
      </div>

      <div className="chat-layout">
        <Card className="chat-card">
          <div className="chat-messages">
            {!messages.length && (
              <div className="chat-welcome">
                <div className="assistant-mark">
                  <Sparkles size={30} />
                </div>
                <h2>
                  Good questions lead
                  <br />
                  to cooler possibilities.
                </h2>
                <p>
                  Explore the evidence for {selected.name}.<br />
                  Your assistant receives actual backend results.
                </p>
                <div className="suggestions">
                  {[
                    "Why is this area hotter?",
                    "Which interventions are feasible?",
                    "Explain the optimization and its limitations.",
                  ].map((q) => (
                    <button key={q} type="button" onClick={() => submit(q)}>
                      {q}
                      <ArrowUpRight size={14} />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div className={"message " + m.role} key={i}>
                {m.role === "user" ? (
                  m.text
                ) : m.response ? (
                  <>
                    <div className="message-provider">
                      <Sparkles size={14} />
                      {m.response.provider}
                      <Badge tone="neutral">
                        {m.response.fallback ? "Template fallback" : "Provider response"}
                      </Badge>
                    </div>
                    <p>{m.response.summary}</p>
                    {m.response.findings.map((f: AIFinding, j: number) => (
                      <p key={j}>
                        {f.statement}{" "}
                        <small className="citation">
                          {f.fact_ids.join(" · ")}
                        </small>
                      </p>
                    ))}
                    <div className="action-tags">
                      {m.response.actions.map((a: string) => (
                        <Badge key={a}>{interventionNames[a] || a}</Badge>
                      ))}
                    </div>
                    <details>
                      <summary>Evidence & limitations</summary>
                      {m.response.facts?.prediction && (
                        <p>
                          Predicted SUHII: {fmt(m.response.facts.prediction.suhii_c, 2)}°C
                          · synthetic.
                        </p>
                      )}
                      {m.response.limitations.map((l: string) => (
                        <p key={l}>{l}</p>
                      ))}
                      {m.response.failures.map((f, idx: number) => (
                        <p key={f.provider || idx}>
                          {f.provider}: {f.reason}
                        </p>
                      ))}
                    </details>
                  </>
                ) : null}
              </div>
            ))}

            {send.isPending && <Pending message="Grounded reasoning in progress…" />}
            {send.isError && (
              <Notice tone="warn">
                {send.error instanceof Error ? send.error.message : "Chat request failed"}
              </Notice>
            )}
          </div>

          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              submit(message);
            }}
          >
            <input
              aria-label="Ask about this zone"
              placeholder="Ask about this zone, a scenario, or an intervention…"
              value={message}
              maxLength={2000}
              onChange={(e) => setMessage(e.target.value)}
            />
            <Button
              type="submit"
              aria-label="Send message"
              disabled={!message.trim() || send.isPending}
            >
              <Send size={18} />
            </Button>
          </form>

          <div className="chat-disclaimer">
            Evidence-grounded support. Verify recommendations before making
            planning decisions.
          </div>
        </Card>

        <ZoneDetails selected={selected} navigate={navigate} />
      </div>
    </>
  );
}
