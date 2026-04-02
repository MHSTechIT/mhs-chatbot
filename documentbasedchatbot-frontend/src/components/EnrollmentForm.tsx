import React, { useState } from 'react';

export interface EnrollmentFormProps {
  onClose: () => void;       // called on Cancel — form dismissed, not submitted
  onSubmit?: () => void;     // called after successful form submission
  language: 'en' | 'ta';
  isDark?: boolean;
}

export const EnrollmentForm: React.FC<EnrollmentFormProps> = ({ onClose, onSubmit, language, isDark = true }) => {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    age: '',
    location: '',
    sugarLevel: ''
  });

  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);


  const isValid = formData.name.trim() && formData.phone.trim() && formData.age.trim() && formData.location.trim();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;

    setIsLoading(true);
    setError(null);

    try {
      // Send enrollment data to backend
      const backendUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').trim();
      const response = await fetch(`${backendUrl}/submit-enrollment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name.trim(),
          phone: formData.phone.trim(),
          age: parseInt(formData.age),
          location: formData.location.trim(),
          sugar_level: formData.sugarLevel.trim() || null
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Submission failed');
      }

      const result = await response.json();
      console.log('✅ Enrollment submitted:', result);
      setSubmitted(true);

      // After showing success for 2 seconds, notify parent of actual submission
      setTimeout(() => {
        onSubmit?.();  // marks enrollment as truly submitted
        onClose();     // hides the form
      }, 2000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to submit enrollment';
      console.error('❌ Enrollment error:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const labels = {
    en: {
      title: 'fill the form',
      name: 'Name *',
      phone: 'Phone Number *',
      age: 'Age *',
      location: 'Location/City *',
      sugarLevel: 'Blood Sugar Level',
      submit: 'Submit',
      success: 'Thank you! We will contact you soon.',
      fillRequired: 'Please fill in all required fields'
    },
    ta: {
      title: 'fill the form',
      name: 'பெயர் *',
      phone: 'தொலைபேசி எண் *',
      age: 'வயது *',
      location: 'இடம்/நகரம் *',
      sugarLevel: 'இரத்த சர்க்கரை அளவு',
      submit: 'சமர்ப்பிக்க',
      success: 'நன்றி! நாங்கள் விரைவில் உங்களை தொடர்புகொள்வோம்.',
      fillRequired: 'தயவுசெய்து அனைத்து கட்டாயமான பகுதிகளை பூர்த்தி செய்யவும்'
    }
  };

  const currentLabels = labels[language];

  const inputClass = isDark
    ? 'w-full px-4 py-2 bg-theme-base border border-theme-cardBorder rounded-lg text-white placeholder-theme-muted focus:outline-none focus:border-theme-accent'
    : 'w-full px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className={`rounded-lg shadow-2xl max-w-md w-full p-6 border transition-colors ${
        isDark ? 'bg-theme-card border-theme-cardBorder' : 'bg-white border-gray-200'
      }`}>
        {!submitted ? (
          <>
            <h2 className={`text-2xl font-bold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>{currentLabels.title}</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name Field */}
              <div>
                <label className={`block text-sm font-semibold mb-2 ${isDark ? 'text-theme-muted' : 'text-gray-600'}`}>
                  {currentLabels.name}
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder={language === 'en' ? 'Enter your name' : 'உங்கள் பெயரை உள்ளிடவும்'}
                  className={inputClass}
                  required
                />
              </div>

              {/* Phone Field */}
              <div>
                <label className={`block text-sm font-semibold mb-2 ${isDark ? 'text-theme-muted' : 'text-gray-600'}`}>
                  {currentLabels.phone}
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder={language === 'en' ? 'Enter your phone number' : 'உங்கள் தொலைபேசி எண்ணை உள்ளிடவும்'}
                  className={inputClass}
                  required
                />
              </div>

              {/* Age Field */}
              <div>
                <label className={`block text-sm font-semibold mb-2 ${isDark ? 'text-theme-muted' : 'text-gray-600'}`}>
                  {currentLabels.age}
                </label>
                <input
                  type="number"
                  name="age"
                  value={formData.age}
                  onChange={handleChange}
                  placeholder={language === 'en' ? 'Enter your age' : 'உங்கள் வயதை உள்ளிடவும்'}
                  className={inputClass}
                  required
                  min="1"
                  max="150"
                />
              </div>

              {/* Location Field */}
              <div>
                <label className={`block text-sm font-semibold mb-2 ${isDark ? 'text-theme-muted' : 'text-gray-600'}`}>
                  {currentLabels.location}
                </label>
                <input
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder={language === 'en' ? 'Enter your city/location' : 'உங்கள் நகரம்/இடத்தை உள்ளிடவும்'}
                  className={inputClass}
                  required
                />
              </div>

              {/* Blood Sugar Level Field (Optional) */}
              <div>
                <label className={`block text-sm font-semibold mb-2 ${isDark ? 'text-theme-muted' : 'text-gray-600'}`}>
                  {currentLabels.sugarLevel}
                </label>
                <input
                  type="text"
                  name="sugarLevel"
                  value={formData.sugarLevel}
                  onChange={handleChange}
                  placeholder={language === 'en' ? 'e.g., 180 mg/dL' : 'எ.கா., 180 mg/dL'}
                  className={inputClass}
                />
              </div>

              {/* Error Message */}
              {error && (
                <p className="text-red-600 text-sm bg-red-50 p-2 rounded border border-red-200">{error}</p>
              )}

              {!isValid && !error && (
                <p className="text-red-600 text-sm">{currentLabels.fillRequired}</p>
              )}

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isLoading}
                  className={`flex-1 px-4 py-2 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed ${
                    isDark
                      ? 'bg-theme-base border border-theme-cardBorder text-white hover:bg-theme-cardBorder'
                      : 'bg-gray-100 border border-gray-300 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {language === 'en' ? 'Cancel' : 'ரத்து'}
                </button>
                <button
                  type="submit"
                  disabled={!isValid || isLoading}
                  className={`flex-1 px-4 py-2 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed font-semibold flex items-center justify-center gap-2 ${
                    isDark
                      ? 'bg-theme-accent text-white hover:bg-theme-accent/80 disabled:bg-theme-cardBorder disabled:text-theme-muted'
                      : 'bg-violet-600 text-white hover:bg-violet-700 disabled:bg-gray-200 disabled:text-gray-400'
                  }`}
                >
                  {isLoading ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.25"></circle>
                        <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {language === 'en' ? 'Submitting...' : 'சமர்ப்பிக்கிறது...'}
                    </>
                  ) : (
                    currentLabels.submit
                  )}
                </button>
              </div>
            </form>
          </>
        ) : (
          // Success Message
          <div className="text-center">
            <div className="text-4xl mb-4">✅</div>
            <p className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{currentLabels.success}</p>
            <p className={`text-sm space-y-1 ${isDark ? 'text-theme-muted' : 'text-gray-600'}`}>
              <div>{language === 'en' ? 'Name: ' : 'பெயர்: '}{formData.name}</div>
              <div>{language === 'en' ? 'Phone: ' : 'தொலைபேசி: '}{formData.phone}</div>
              <div>{language === 'en' ? 'Age: ' : 'வயது: '}{formData.age}</div>
              <div>{language === 'en' ? 'Location: ' : 'இடம்: '}{formData.location}</div>
              {formData.sugarLevel && <div>{language === 'en' ? 'Blood Sugar: ' : 'இரத்த சர்க்கரை: '}{formData.sugarLevel}</div>}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
