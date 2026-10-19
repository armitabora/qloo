import { useState, useEffect } from 'react'

function App() {
  const [formData, setFormData] = useState({ city: 'Tokyo', music: '', film: '', vibe: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [loadingTextIndex, setLoadingTextIndex] = useState(0);
  const [itinerary, setItinerary] = useState(null);
  const [validationError, setValidationError] = useState(false);
  const [apiError, setApiError] = useState(false);

  const loadingPhrases = [
    "Analyzing your taste...",
    "Mapping the city...",
    "Writing your itinerary...",
    "Finalizing details..."
  ];

  // Cycle through loading phrases
  useEffect(() => {
    let interval;
    if (isLoading) {
      interval = setInterval(() => {
        setLoadingTextIndex((prev) => (prev + 1) % loadingPhrases.length);
      }, 2000);
    } else {
      setLoadingTextIndex(0);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError(false);
    setApiError(false);

    // Validation: At least one anchor must be filled
    if (!formData.music && !formData.film && !formData.vibe) {
      setValidationError(true);
      return;
    }

    setIsLoading(true);
    
    try {
      const res = await fetch('http://localhost:8000/api/generate-itinerary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (!res.ok) throw new Error("API failed");
      
      const data = await res.json();
      
      // Artificial delay to show off the cycling loading text for the demo!
      setTimeout(() => {
        setItinerary(data);
        setIsLoading(false);
      }, 6000);
      
    } catch (error) {
      console.error("Error fetching itinerary:", error);
      setTimeout(() => {
        setApiError(true);
        setIsLoading(false);
      }, 2000);
    }
  };

  const resetForm = () => {
    setItinerary(null);
    setApiError(false);
    setFormData({ city: 'Tokyo', music: '', film: '', vibe: '' });
  };

  return (
    <div className="min-h-screen bg-[#121212] text-[#E0E0E0] font-sans selection:bg-gray-700 p-6">
      <div className="max-w-2xl mx-auto pt-12">
        
        {/* Header */}
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">VibeGuide.</h1>
          <p className="text-gray-400">Enter your cultural anchors. Discover your city.</p>
        </header>

        {/* Input Form */}
        {!itinerary && !isLoading && !apiError && (
          <form onSubmit={handleSubmit} className="space-y-8 flex flex-col items-center animate-in fade-in duration-500">
            <div className="w-full max-w-md space-y-6">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Destination</label>
                <select
                  className="w-full bg-transparent border-b border-gray-600 pb-2 text-lg focus:outline-none focus:border-white transition-colors cursor-pointer"
                  value={formData.city}
                  onChange={(e) => setFormData({...formData, city: e.target.value})}
                >
                  <option value="Tokyo" className="bg-gray-800">Tokyo</option>
                  <option value="New York" className="bg-gray-800">New York</option>
                </select>
              </div>
              
              {/* Validation Warning */}
              {validationError && (
                <div className="text-red-400 text-sm font-medium text-center bg-red-900/20 py-2 rounded">
                  Please enter at least one cultural anchor.
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Favorite Music</label>
                <input
                  type="text" placeholder="e.g., Radiohead, Daft Punk..."
                  className={`w-full bg-transparent border-b pb-2 text-lg focus:outline-none transition-colors placeholder:text-gray-700 ${validationError ? 'border-red-500' : 'border-gray-600 focus:border-white'}`}
                  value={formData.music} onChange={(e) => {setFormData({...formData, music: e.target.value}); setValidationError(false);}}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Favorite Film/Director</label>
                <input
                  type="text" placeholder="e.g., Studio Ghibli, Wes Anderson..."
                  className={`w-full bg-transparent border-b pb-2 text-lg focus:outline-none transition-colors placeholder:text-gray-700 ${validationError ? 'border-red-500' : 'border-gray-600 focus:border-white'}`}
                  value={formData.film} onChange={(e) => {setFormData({...formData, film: e.target.value}); setValidationError(false);}}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Desired Vibe</label>
                <input
                  type="text" placeholder="e.g., Cyberpunk neon, Cozy lo-fi..."
                  className={`w-full bg-transparent border-b pb-2 text-lg focus:outline-none transition-colors placeholder:text-gray-700 ${validationError ? 'border-red-500' : 'border-gray-600 focus:border-white'}`}
                  value={formData.vibe} onChange={(e) => {setFormData({...formData, vibe: e.target.value}); setValidationError(false);}}
                />
              </div>
            </div>

            <button
              type="submit"
              className="mt-8 px-8 py-3 bg-white text-black font-medium rounded-full hover:bg-gray-200 transition-colors"
            >
              Generate My Day ✨
            </button>
          </form>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center space-y-6 mt-20 animate-in fade-in duration-500">
            <div className="w-8 h-8 border-4 border-gray-600 border-t-white rounded-full animate-spin"></div>
            <p className="text-lg text-gray-300 font-medium tracking-wide transition-opacity duration-300">
              {loadingPhrases[loadingTextIndex]}
            </p>
          </div>
        )}

        {/* Error State */}
        {apiError && (
          <div className="flex flex-col items-center justify-center space-y-6 mt-20 animate-in fade-in duration-500 text-center">
            <div className="text-4xl">💔</div>
            <p className="text-lg text-gray-300 max-w-md">
              Vibe check failed. The city might be too sleepy right now, or our AI needs a coffee.
            </p>
            <button
              onClick={resetForm}
              className="mt-4 px-6 py-2 border border-gray-600 text-gray-300 rounded-full hover:bg-gray-800 transition-colors"
            >
              Try Different Anchors
            </button>
          </div>
        )}

        {/* Results Timeline */}
        {itinerary && !isLoading && (
          <div className="animate-in fade-in duration-700 slide-in-from-bottom-4">
            <h2 className="text-2xl font-semibold mb-8 text-center text-white">Your Vibe in {itinerary.city}</h2>
            <div className="relative border-l border-gray-700 ml-4 space-y-10 pb-8">
              {itinerary.stops.map((stop, idx) => (
                <div key={idx} className="pl-8 relative">
                  {/* Timeline dot */}
                  <div className="absolute w-3 h-3 bg-white rounded-full -left-[6.5px] top-1.5"></div>
                  
                  <div className="text-xs text-gray-500 font-bold uppercase tracking-wider mb-1">{stop.phase}</div>
                  <div className="text-xl font-medium text-white mb-3">{stop.venue}</div>
                  <blockquote className="bg-[#1e1e1e] border-l-2 border-gray-500 p-4 rounded-r-lg text-sm text-gray-300 italic">
                    ✨ {stop.vibe_narrative}
                  </blockquote>
                </div>
              ))}
            </div>
            <div className="text-center mt-12">
              <button
                onClick={resetForm}
                className="text-gray-400 hover:text-white border border-gray-600 hover:border-white px-6 py-2 rounded-full transition-colors"
              >
                Plan Another Day
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App