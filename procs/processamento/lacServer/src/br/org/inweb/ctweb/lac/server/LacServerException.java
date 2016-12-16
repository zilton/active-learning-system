package br.org.inweb.ctweb.lac.server;

public class LacServerException extends RuntimeException{
	private static final long serialVersionUID = 6922119468096735681L;

	public LacServerException() {
		super();
	}

	public LacServerException(String message, Throwable cause,
			boolean enableSuppression, boolean writableStackTrace) {
		super(message, cause, enableSuppression, writableStackTrace);
	}

	public LacServerException(String message, Throwable cause) {
		super(message, cause);
	}

	public LacServerException(String message) {
		super(message);
	}

	public LacServerException(Throwable cause) {
		super(cause);
	}
	
}
