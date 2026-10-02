import { useCallback, useEffect, useState } from "react";

export function useObjectUrl(initialFile = null) {
  const [picked, setPicked] = useState(() =>
    initialFile ? { file: initialFile, url: URL.createObjectURL(initialFile) } : null
  );

  useEffect(() => {
    const current = picked?.url;
    return () => {
      if (current) URL.revokeObjectURL(current);
    };
  }, [picked]);

  const select = useCallback(
    (file) => setPicked(file ? { file, url: URL.createObjectURL(file) } : null),
    []
  );

  return [picked, select];
}