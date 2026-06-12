package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_3Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        String input = "First line\nSecond line\nThird line\nFourth line";
        Reader stringReader = new StringReader(input);
        reader = new ExtendedBufferedReader(stringReader);
    }

    @Test
    void testExtendedBufferedReader_read() throws Exception {
        int firstChar = reader.read();
        Assertions.assertEquals('F', firstChar);
    }

    @Test
    void testExtendedBufferedReader_readAgain() throws Exception {
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        
        reader.read(); // Advance the reader
        int result = (int) readAgainMethod.invoke(reader);
        Assertions.assertNotEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testExtendedBufferedReader_read_charArray() throws Exception {
        char[] buffer = new char[20];
        int charsRead = reader.read(buffer, 0, 20);
        Assertions.assertTrue(charsRead > 0);
        Assertions.assertEquals("First line\nSecond li", new String(buffer, 0, charsRead));
    }

    @Test
    void testExtendedBufferedReader_readLineWithMixedContent() throws Exception {
        String input = "First line\n\nSecond line\n\n\nThird line";
        Reader stringReader = new StringReader(input);
        reader = new ExtendedBufferedReader(stringReader);
        
        String line = reader.readLine();
        Assertions.assertEquals("First line", line);
        
        line = reader.readLine();
        Assertions.assertEquals("", line); // Check for the first empty line
        
        line = reader.readLine();
        Assertions.assertEquals("Second line", line); // Check for the second line
        
        line = reader.readLine();
        Assertions.assertEquals("", line); // Check for the third empty line
        
        line = reader.readLine();
        Assertions.assertNotNull(line); // Ensure that the line is not null
        Assertions.assertEquals("Third line", line); // Check for the fourth line
    }

    @Test
    void testExtendedBufferedReader_lookAhead() throws Exception {
        Method lookAheadMethod = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAheadMethod.setAccessible(true);
        
        int peekedChar = (int) lookAheadMethod.invoke(reader);
        Assertions.assertEquals('F', peekedChar);
        
        reader.read(); // Advance the reader
        peekedChar = (int) lookAheadMethod.invoke(reader);
        Assertions.assertEquals('i', peekedChar); // Check the next character
    }

    @Test
    void testExtendedBufferedReader_getLineNumber() throws Exception {
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        
        int lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(0, lineNumber);
        
        reader.readLine(); // Advance to the next line
        lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber); // Line number should now be 1
    }
}