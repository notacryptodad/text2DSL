import AdminSidebar from './AdminSidebar'

function AdminLayout({ children }) {
  return (
    <div className="flex min-h-[calc(100vh-73px)] bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}

export default AdminLayout
