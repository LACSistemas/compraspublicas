"use client";

import { useEffect, useRef, useState } from "react";

interface OpcoesPolling<T> {
  fetchFn: () => Promise<T>;
  intervalMs: number;
  shouldStop: (data: T) => boolean;
}

interface ResultadoPolling<T> {
  data: T | null;
  erro: Error | null;
  parado: boolean;
}

// Hook genérico de polling: chama `fetchFn` a cada `intervalMs` até `shouldStop(data)`
// retornar true (ou até a chamada falhar). `fetchFn`/`shouldStop` são lidos via ref a cada
// tick, então não precisam ser estáveis entre renders (evita reiniciar o polling sem querer).
export function usePolling<T>({
  fetchFn,
  intervalMs,
  shouldStop,
}: OpcoesPolling<T>): ResultadoPolling<T> {
  const [data, setData] = useState<T | null>(null);
  const [erro, setErro] = useState<Error | null>(null);
  const [parado, setParado] = useState(false);

  const fetchFnRef = useRef(fetchFn);
  const shouldStopRef = useRef(shouldStop);
  fetchFnRef.current = fetchFn;
  shouldStopRef.current = shouldStop;

  useEffect(() => {
    let cancelado = false;
    let timeoutId: ReturnType<typeof setTimeout>;

    async function tick() {
      try {
        const resultado = await fetchFnRef.current();
        if (cancelado) return;
        setData(resultado);
        if (shouldStopRef.current(resultado)) {
          setParado(true);
          return;
        }
      } catch (e) {
        if (cancelado) return;
        setErro(e instanceof Error ? e : new Error(String(e)));
        setParado(true);
        return;
      }
      timeoutId = setTimeout(tick, intervalMs);
    }

    tick();

    return () => {
      cancelado = true;
      clearTimeout(timeoutId);
    };
  }, [intervalMs]);

  return { data, erro, parado };
}
