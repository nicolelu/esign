'use client';

import { CheckCircle } from 'lucide-react';

export default function SigningCompletePage() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center max-w-md p-8">
        <CheckCircle className="w-16 h-16 mx-auto mb-6 text-green-500" />
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Signing Complete!
        </h1>
        <p className="text-gray-600 mb-6">
          Thank you for signing the document. You will receive an email with the
          completed document once all parties have signed.
        </p>
        <p className="text-sm text-gray-500">
          You may close this window now.
        </p>
      </div>
    </div>
  );
}
