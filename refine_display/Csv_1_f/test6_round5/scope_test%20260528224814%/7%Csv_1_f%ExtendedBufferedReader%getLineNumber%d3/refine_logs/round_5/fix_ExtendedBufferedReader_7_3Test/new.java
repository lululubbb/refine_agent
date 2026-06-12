package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;

class ExtendedBufferedReader_7_3Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
    }

    @Test
    void testgetLineNumber_initialValue() throws Exception {
        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingLines() throws Exception {
        reader.readLine(); // Reads "Line 1"
        reader.readLine(); // Reads "Line 2"

        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testgetLineNumber_afterMultipleReads() throws Exception {
        reader.readLine(); // Reads "Line 1"
        reader.readLine(); // Reads "Line 2"
        reader.readLine(); // Reads "Line 3"

        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testgetLineNumber_afterNoReads() throws Exception {
        // No lines read
        int lineNumber = reader.getLineNumber();
        Assertions.assertEquals(0, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingEmptyLines() throws Exception {
        ExtendedBufferedReader emptyLineReader = new ExtendedBufferedReader(new StringReader("\n\n"));
        emptyLineReader.readLine(); // Reads empty line
        emptyLineReader.readLine(); // Reads another empty line

        int lineNumber = emptyLineReader.getLineNumber();
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testgetLineNumber_withMixedContent() throws Exception {
        ExtendedBufferedReader mixedContentReader = new ExtendedBufferedReader(new StringReader("Line 1\n\nLine 2\nLine 3\n"));
        mixedContentReader.readLine(); // Reads "Line 1"
        mixedContentReader.readLine(); // Reads empty line
        mixedContentReader.readLine(); // Reads "Line 2"

        int lineNumber = mixedContentReader.getLineNumber();
        Assertions.assertEquals(3, lineNumber);
    }

    @Test
    void testgetLineNumber_afterReadingAllLines() throws Exception {
        reader.readLine(); // Reads "Line 1"
        reader.readLine(); // Reads "Line 2"
        reader.readLine(); // Reads "Line 3"
        int lineNumber = reader.getLineNumber(); // Should be 3
        Assertions.assertEquals(3, lineNumber);
        
        // Try reading again after all lines are read
        String additionalRead = reader.readLine(); // Should return null
        Assertions.assertEquals(null, additionalRead);
        Assertions.assertEquals(3, reader.getLineNumber()); // Line number should still be 3
    }

    @Test
    void testgetLineNumber_withEmptyReader() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        int lineNumber = emptyReader.getLineNumber(); // Should be 0
        Assertions.assertEquals(0, lineNumber);
        
        String result = emptyReader.readLine(); // Should return null
        Assertions.assertEquals(null, result);
        Assertions.assertEquals(0, emptyReader.getLineNumber()); // Line number should still be 0
    }

    @Test
    void testRead() throws Exception {
        int charRead = reader.read(); // Should read the first character 'L'
        Assertions.assertEquals('L', charRead);
        Assertions.assertEquals(0, reader.getLineNumber()); // Line number should still be 0
    }

    @Test
    void testReadAgain() throws Exception {
        int charRead1 = reader.read(); // Reads 'L'
        int charRead2 = reader.read(); // Should read the next character 'i'
        Assertions.assertEquals('i', charRead2);
    }

    @Test
    void testReadWithEndOfStream() throws Exception {
        reader.readLine(); // Reads "Line 1"
        reader.readLine(); // Reads "Line 2"
        reader.readLine(); // Reads "Line 3"
        int charRead = reader.read(); // Should return -1 (end of stream)
        Assertions.assertEquals(-1, charRead);
    }

    @Test
    void testLookAhead() throws Exception {
        int charRead = reader.lookAhead(); // Should peek the first character 'L'
        Assertions.assertEquals('L', charRead);
        Assertions.assertEquals(0, reader.getLineNumber()); // Line number should still be 0
    }
}