package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Constructor;
import java.lang.reflect.Modifier;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_10_2Test {

    private CSVRecord csvRecord;
    private long recordNumber = 123L;

    @BeforeEach
    public void setUp() throws Exception {
        String[] values = new String[] {"value1", "value2"};
        Map<String, Integer> mapping = new java.util.HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        String comment = "comment";

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(
                String[].class, Map.class, String.class, long.class);
        if (!Modifier.isPublic(constructor.getModifiers()) || !constructor.canAccess(null)) {
            constructor.setAccessible(true);
        }
        csvRecord = constructor.newInstance(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    public void testGetRecordNumber() {
        assertEquals(recordNumber, csvRecord.getRecordNumber());
    }
}