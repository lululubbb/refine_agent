package org.apache.commons.csv;
import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_2_6Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        int firstChar = ebr.read();
        Assertions.assertEquals('H', firstChar);

        int secondChar = ebr.read();
        Assertions.assertEquals('e', secondChar);

        int thirdChar = ebr.read();
        Assertions.assertEquals('l', thirdChar);
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        String input = "Hello\r\nWorld\r\n";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        ebr.read(); // 'H'
        ebr.read(); // 'e'
        ebr.read(); // 'l'
        ebr.read(); // 'l'
        ebr.read(); // 'o'
        int lineBreak = ebr.read(); // '\r'
        Assertions.assertEquals('\r', lineBreak);
        
        int newLine = ebr.read(); // '\n'
        Assertions.assertEquals('\n', newLine);
        
        int nextChar = ebr.read(); // 'W'
        Assertions.assertEquals('W', nextChar);
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        int result = ebr.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testRead_multipleLineBreaks() throws Exception {
        String input = "Line1\nLine2\nLine3\n";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        ebr.read(); // 'L'
        ebr.read(); // 'i'
        ebr.read(); // 'n'
        ebr.read(); // 'e'
        ebr.read(); // '1'
        ebr.read(); // '\n' -> lineCounter should increase

        ebr.read(); // 'L'
        ebr.read(); // 'i'
        ebr.read(); // 'n'
        ebr.read(); // 'e'
        ebr.read(); // '2'
        ebr.read(); // '\n' -> lineCounter should increase

        ebr.read(); // 'L'
        ebr.read(); // 'i'
        ebr.read(); // 'n'
        ebr.read(); // 'e'
        ebr.read(); // '3'
        ebr.read(); // '\n' -> lineCounter should increase
    }

    @Test
    void testRead_carriageReturn() throws Exception {
        String input = "Hello\rWorld";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        ebr.read(); // 'H'
        ebr.read(); // 'e'
        ebr.read(); // 'l'
        ebr.read(); // 'l'
        ebr.read(); // 'o'
        int carriageReturn = ebr.read(); // '\r'
        Assertions.assertEquals('\r', carriageReturn);
        
        int nextChar = ebr.read(); // 'W'
        Assertions.assertEquals('W', nextChar);
    }
}