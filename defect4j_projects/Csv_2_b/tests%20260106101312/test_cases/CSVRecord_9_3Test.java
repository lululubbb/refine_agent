package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
import java.util.Collections;
import java.util.Map;
import java.lang.reflect.Constructor;

public class CSVRecord_9_3Test {

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance((Object) values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    public void testGetComment_NonNullComment() throws Exception {
        String[] values = new String[] {"a", "b"};
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);

        assertEquals(comment, record.getComment());
    }

    @Test
    @Timeout(8000)
    public void testGetComment_NullComment() throws Exception {
        String[] values = new String[] {"x", "y"};
        Map<String, Integer> mapping = Collections.emptyMap();
        String comment = null;
        long recordNumber = 2L;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);

        assertNull(record.getComment());
    }
}