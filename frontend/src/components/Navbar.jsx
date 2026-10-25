import { useState } from 'react';
import { Bell, Bot, ChevronDown, CircleUserRound, FileClock, LayoutDashboard, LogOut, Menu, ScanLine, Stethoscope, X } from 'lucide-react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { isAuthenticated, currentUser, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (location.pathname === '/login' || location.pathname === '/register') {
    return null;
  }

  const links = isAuthenticated
    ? [
        { to: '/home', label: 'Dashboard', icon: LayoutDashboard },
        { to: '/home#upload-section', label: 'Analyze', icon: ScanLine },
        { to: '/assistant', label: 'Chatbot Assistant', icon: Bot },
        { to: '/history', label: 'History', icon: FileClock },
        { to: '/how-it-works', label: 'How It Works', icon: Stethoscope },
      ]
    : [
        { to: '/login', label: 'Login', icon: CircleUserRound },
        { to: '/register', label: 'Register', icon: Stethoscope },
      ];

  const handleLogout = () => {
    logout();
    navigate('/login');
    setIsOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
      <nav className="mx-auto flex max-w-[1380px] items-center justify-between px-4 py-3 sm:px-6 lg:px-8" aria-label="Main navigation">
        <Link to={isAuthenticated ? '/home' : '/login'} className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#0F2747] text-white shadow-sm">
            <ScanLine className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <p className="text-[15px] font-bold tracking-tight text-[#0F2747]">RetinalAI</p>
            <p className="hidden text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-400 sm:block">AI-powered retinal analysis</p>
          </div>
        </Link>

        <div className="hidden items-center gap-2 md:flex">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={label}
              to={to}
              className={({ isActive }) =>
                `inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
                  isActive || (label === 'Analyze' && location.pathname.startsWith('/analysis'))
                    ? 'bg-sky-50 text-[#1677FF] ring-1 ring-sky-200'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-[#0F2747]'
                }`
              }
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              {label}
            </NavLink>
          ))}

          {isAuthenticated && <NavLink to="/profile" className="ml-3 inline-flex items-center gap-2 border-l border-slate-200 pl-4 text-sm font-semibold text-[#0F2747] hover:text-[#1677FF]"><CircleUserRound className="h-5 w-5 text-sky-600" aria-hidden="true" />{currentUser?.fullName?.split(' ')[0] || 'Profile'}<ChevronDown className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" /></NavLink>}
          {isAuthenticated && <button type="button" onClick={handleLogout} className="ml-2 rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600" aria-label="Log out" title="Log out"><LogOut className="h-4 w-4" aria-hidden="true" /></button>}
        </div>

        <div className="flex items-center gap-3 md:hidden">
          {isAuthenticated && <Bell className="h-5 w-5 text-slate-400" aria-hidden="true" />}
          <button
            type="button"
            aria-label={isOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={isOpen}
            onClick={() => setIsOpen((value) => !value)}
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-slate-300"
          >
            {isOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </nav>

      {isOpen && (
        <div className="border-t border-slate-200 bg-white md:hidden">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-4">
            {links.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={label}
                to={to}
                onClick={() => setIsOpen(false)}
                className={({ isActive }) =>
                  `inline-flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition ${
                    isActive || (label === 'Analyze' && location.pathname.startsWith('/analysis'))
                      ? 'bg-sky-50 text-sky-700 ring-1 ring-sky-200'
                      : 'text-slate-700 hover:bg-slate-100'
                  }`
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </NavLink>
            ))}

            {isAuthenticated && (
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center justify-center gap-3 rounded-xl bg-slate-900 px-4 py-3 text-sm font-medium text-white"
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Logout
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
