package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_2_6Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        Assertions.assertEquals('H', ebr.read());
        Assertions.assertEquals('e', ebr.read());
        Assertions.assertEquals('l', ebr.read());
        Assertions.assertEquals('l', ebr.read());
        Assertions.assertEquals('o', ebr.read());
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
        Assertions.assertEquals('\r', ebr.read());
        Assertions.assertEquals('\n', ebr.read());
        Assertions.assertEquals('W', ebr.read());
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, ebr.read());
    }

    @Test
    void testRead_multipleLineBreaks() throws Exception {
        String input = "Line1\nLine2\nLine3\n";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        Assertions.assertEquals('L', ebr.read());
        Assertions.assertEquals('i', ebr.read());
        Assertions.assertEquals('n', ebr.read());
        Assertions.assertEquals('e', ebr.read());
        Assertions.assertEquals('1', ebr.read());
        Assertions.assertEquals('\n', ebr.read()); // lineCounter should increase

        Assertions.assertEquals('L', ebr.read());
        Assertions.assertEquals('i', ebr.read());
        Assertions.assertEquals('n', ebr.read());
        Assertions.assertEquals('e', ebr.read());
        Assertions.assertEquals('2', ebr.read());
        Assertions.assertEquals('\n', ebr.read()); // lineCounter should increase

        Assertions.assertEquals('L', ebr.read());
        Assertions.assertEquals('i', ebr.read());
        Assertions.assertEquals('n', ebr.read());
        Assertions.assertEquals('e', ebr.read());
        Assertions.assertEquals('3', ebr.read());
        Assertions.assertEquals('\n', ebr.read()); // lineCounter should increase
    }

    @Test
    void testRead_carriageReturn() throws Exception {
        String input = "Hello\rWorld";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        Assertions.assertEquals('H', ebr.read());
        Assertions.assertEquals('e', ebr.read());
        Assertions.assertEquals('l', ebr.read());
        Assertions.assertEquals('l', ebr.read());
        Assertions.assertEquals('o', ebr.read());
        Assertions.assertEquals('\r', ebr.read());
        Assertions.assertEquals('W', ebr.read());
    }

    @Test
    void testRead_boundaryValue() throws Exception {
        String input = "\n";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        Assertions.assertEquals('\n', ebr.read()); // Read a single line break
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, ebr.read()); // End of stream
    }

    @Test
    void testRead_exceptionHandling() throws Exception {
        Assertions.assertThrows(IOException.class, () -> {
            Reader reader = new Reader() {
                @Override
                public int read(char[] cbuf, int off, int len) throws IOException {
                    throw new IOException("Simulated IOException");
                }
                @Override
                public void close() throws IOException {}
            };
            ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
            ebr.read();
        });
    }
}