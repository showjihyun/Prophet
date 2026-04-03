/**
 * Auto-generated from SPEC: docs/spec/06_API_SPEC.md
 * SPEC Version: 0.1.0
 *
 * @spec docs/spec/06_API_SPEC.md#auth
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

const mockLogin = vi.fn();
const mockRegister = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    auth: {
      login: (...args: unknown[]) => mockLogin(...args),
      register: (...args: unknown[]) => mockRegister(...args),
    },
  },
}));

import LoginPage from '@/pages/LoginPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    localStorage.clear();
  });

  /** @spec 06_API_SPEC.md#auth-layout */
  describe('Layout', () => {
    it('renders MCASP Prophet logo/brand text', () => {
      renderPage();
      expect(screen.getByText('MCASP Prophet')).toBeInTheDocument();
    });

    it('renders Sign in heading', () => {
      renderPage();
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Sign in');
    });

    it('renders credentials subtitle', () => {
      renderPage();
      expect(
        screen.getByText('Enter your credentials to continue.'),
      ).toBeInTheDocument();
    });
  });

  /** @spec 06_API_SPEC.md#auth-form-fields */
  describe('Form Fields', () => {
    it('renders username label', () => {
      renderPage();
      expect(screen.getByText('Username')).toBeInTheDocument();
    });

    it('renders username input field', () => {
      renderPage();
      expect(screen.getByPlaceholderText('username')).toBeInTheDocument();
    });

    it('renders password label', () => {
      renderPage();
      expect(screen.getByText('Password')).toBeInTheDocument();
    });

    it('renders password input field', () => {
      renderPage();
      expect(screen.getByPlaceholderText('password')).toBeInTheDocument();
    });

    it('renders password field as type=password', () => {
      renderPage();
      const passwordInput = screen.getByPlaceholderText('password');
      expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  /** @spec 06_API_SPEC.md#auth-actions */
  describe('Action Buttons', () => {
    it('renders Login button', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    it('renders Register button', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
    });

    it('Login button is disabled when fields are empty', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /login/i })).toBeDisabled();
    });

    it('Register button is disabled when fields are empty', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /register/i })).toBeDisabled();
    });

    it('buttons become enabled when both fields are filled', async () => {
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'testuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'testpass' },
      });
      expect(screen.getByRole('button', { name: /login/i })).not.toBeDisabled();
      expect(screen.getByRole('button', { name: /register/i })).not.toBeDisabled();
    });
  });

  /** @spec 06_API_SPEC.md#auth-login-flow */
  describe('Login Flow', () => {
    it('calls apiClient.auth.login with username and password', async () => {
      mockLogin.mockResolvedValue({ token: 'tok-123', username: 'testuser' });
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'testuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'testpass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /login/i }));
      await waitFor(() =>
        expect(mockLogin).toHaveBeenCalledWith('testuser', 'testpass'),
      );
    });

    it('stores token in localStorage after successful login', async () => {
      mockLogin.mockResolvedValue({ token: 'tok-123', username: 'testuser' });
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'testuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'testpass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /login/i }));
      await waitFor(() => expect(localStorage.getItem('prophet-token')).toBe('tok-123'));
    });

    it('navigates to /projects after successful login', async () => {
      mockLogin.mockResolvedValue({ token: 'tok-123', username: 'testuser' });
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'testuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'testpass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /login/i }));
      await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/projects'));
    });

    it('shows error message on failed login', async () => {
      mockLogin.mockRejectedValue(new Error('Unauthorized'));
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'testuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'wrongpass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /login/i }));
      await waitFor(() =>
        expect(screen.getByText('Invalid username or password.')).toBeInTheDocument(),
      );
    });
  });

  /** @spec 06_API_SPEC.md#auth-register-flow */
  describe('Register Flow', () => {
    it('calls apiClient.auth.register then login on register button click', async () => {
      mockRegister.mockResolvedValue({});
      mockLogin.mockResolvedValue({ token: 'tok-new', username: 'newuser' });
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'newuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'newpass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith('newuser', 'newpass');
        expect(mockLogin).toHaveBeenCalledWith('newuser', 'newpass');
      });
    });

    it('navigates to /projects after successful registration', async () => {
      mockRegister.mockResolvedValue({});
      mockLogin.mockResolvedValue({ token: 'tok-new', username: 'newuser' });
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'newuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'newpass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
      await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/projects'));
    });

    it('shows username taken error when register returns 409', async () => {
      mockRegister.mockRejectedValue(new Error('409 Conflict'));
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'existinguser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'somepass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
      await waitFor(() =>
        expect(screen.getByText('Username already taken.')).toBeInTheDocument(),
      );
    });

    it('shows generic registration failed error on other errors', async () => {
      mockRegister.mockRejectedValue(new Error('Internal Server Error'));
      renderPage();
      fireEvent.change(screen.getByPlaceholderText('username'), {
        target: { value: 'newuser' },
      });
      fireEvent.change(screen.getByPlaceholderText('password'), {
        target: { value: 'newpass' },
      });
      fireEvent.click(screen.getByRole('button', { name: /register/i }));
      await waitFor(() =>
        expect(screen.getByText('Registration failed.')).toBeInTheDocument(),
      );
    });
  });
});
