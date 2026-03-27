import React from 'react';
import ProviderSelect from './components/ProviderSelect';
import { Database } from 'lucide-react';

const mockProviders = [
  { id: '1', name: 'PostgreSQL', type: 'Database', icon: <Database /> },
  { id: '2', name: 'MySQL', type: 'Database', icon: <Database /> }
];

export default function VerifyComponent() {
  const [selected, setSelected] = React.useState(mockProviders[0]);

  return (
    <div className="p-8 max-w-md mx-auto">
      <h1 className="text-xl font-bold mb-4">Provider Select Verify</h1>
      <ProviderSelect
        providers={mockProviders}
        selected={selected}
        onChange={setSelected}
      />
    </div>
  );
}
