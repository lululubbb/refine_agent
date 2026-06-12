package org.apache.commons.csv;

import java.io.BufferedReader;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ExtendedBufferedReader_2_4Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        Reader mockReader = new StringReader("line1\nline2\r\nline3");
        reader = new ExtendedBufferedReader(mockReader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        assertEquals('l', reader.read());
        assertEquals('i', reader.read());
        assertEquals('n', reader.read());
        assertEquals('e', reader.read());
        assertEquals('1', reader.read());
        assertEquals('\n', reader.read());
        assertEquals('l', reader.read());
        assertEquals('i', reader.read());
        assertEquals('n', reader.read());
        assertEquals('e', reader.read());
        assertEquals('2', reader.read());
        assertEquals('\r', reader.read());
        assertEquals('l', reader.read());
        assertEquals('i', reader.read());
        assertEquals('n', reader.read());
        assertEquals('e', reader.read());
        assertEquals('3', reader.read());
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
        
        // Assert line counter after reading
        assertEquals(3, getLineNumber(reader));
    }

    @Test
    void testRead_lineCounterIncrement() throws Exception {
        reader.read(); // Read 'l'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '1'
        reader.read(); // Read '\n'
        
        // Check line counter after reading first line
        assertEquals(1, getLineNumber(reader));
        
        reader.read(); // Read 'l'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '2'
        reader.read(); // Read '\r'
        reader.read(); // Read 'l'
        reader.read(); // Read 'i'
        reader.read(); // Read 'n'
        reader.read(); // Read 'e'
        reader.read(); // Read '3'
        
        // Check line counter after reading second line
        assertEquals(2, getLineNumber(reader));
    }

    private int getLineNumber(ExtendedBufferedReader reader) throws Exception {
        java.lang.reflect.Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}