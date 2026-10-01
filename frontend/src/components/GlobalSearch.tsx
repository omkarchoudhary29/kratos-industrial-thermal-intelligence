import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  MapPin,
  Factory,
  Flame,
  FileText,
  BookmarkPlus,
  Crosshair,
  X,
  Loader2,
  ChevronRight,
} from 'lucide-react';
import { api } from '../services/api';
import { SearchResult } from '../types';

interface GlobalSearchProps {
  onSelectResult: (result: SearchResult) => void;
  className?: string;
}

export const GlobalSearch: React.FC<GlobalSearchProps> = ({ onSelectResult, className = '' }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Keyboard shortcut Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Debounced search
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await api.search(trimmed, 12);
        setResults(res.results || []);
        setIsOpen(true);
      } catch (err) {
        console.warn('Global search query failed:', err);
      } finally {
        setIsLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (item: SearchResult) => {
    onSelectResult(item);
    setIsOpen(false);
    setQuery('');
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'regions':
        return <MapPin className="w-3.5 h-3.5 text-blue-600" />;
      case 'facilities':
        return <Factory className="w-3.5 h-3.5 text-indigo-600" />;
      case 'clusters':
        return <Flame className="w-3.5 h-3.5 text-amber-500" />;
      case 'coordinates':
        return <Crosshair className="w-3.5 h-3.5 text-emerald-600" />;
      case 'reports':
        return <FileText className="w-3.5 h-3.5 text-purple-600" />;
      case 'tasks':
        return <BookmarkPlus className="w-3.5 h-3.5 text-orange-500" />;
      default:
        return <Search className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category) {
      case 'regions':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'facilities':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'clusters':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'coordinates':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'reports':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'tasks':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative flex items-center">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results.length > 0 || query.trim()) setIsOpen(true);
          }}
          placeholder="Search corridors, OSM assets, clusters, coordinates (e.g. 24.1, 82.6)..."
          className="w-full bg-slate-50 border border-slate-200 hover:border-slate-300 focus:border-blue-500 focus:bg-white text-xs text-slate-900 placeholder-slate-400 font-medium py-1.5 pl-9 pr-14 rounded-lg outline-none transition-all shadow-sm"
        />

        <div className="absolute right-2.5 flex items-center gap-1">
          {isLoading && <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />}
          {query && !isLoading && (
            <button
              onClick={() => {
                setQuery('');
                setResults([]);
                setIsOpen(false);
              }}
              className="p-0.5 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-200"
            >
              <X className="w-3 h-3" />
            </button>
          )}
          {!query && (
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-100 border border-slate-200 rounded">
              ⌘K
            </kbd>
          )}
        </div>
      </div>

      {/* Dropdown Results */}
      {isOpen && (query.trim().length > 0 || results.length > 0) && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl z-50 max-h-96 overflow-y-auto overflow-x-hidden divide-y divide-slate-100 animate-fadeIn">
          {results.length === 0 && !isLoading && (
            <div className="p-4 text-center text-xs text-slate-500">
              No matching regions, facilities, or clusters found for "{query}".
            </div>
          )}

          {results.map((item) => (
            <button
              key={`${item.category}_${item.id}`}
              onClick={() => handleSelect(item)}
              className="w-full text-left px-3.5 py-2.5 hover:bg-slate-50 transition-colors flex items-center justify-between group"
            >
              <div className="flex items-start gap-2.5 min-w-0 pr-2">
                <div className="p-1.5 rounded-md bg-slate-100 group-hover:bg-white border border-slate-200/80 mt-0.5 flex-shrink-0">
                  {getCategoryIcon(item.category)}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-900 truncate">
                      {item.title}
                    </span>
                    <span
                      className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded border font-medium ${getCategoryBadgeClass(
                        item.category
                      )}`}
                    >
                      {item.category}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 truncate mt-0.5">
                    {item.subtitle}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 text-slate-400 group-hover:text-blue-600 flex-shrink-0">
                <span className="text-[10px] font-mono hidden md:inline">Fly to</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
