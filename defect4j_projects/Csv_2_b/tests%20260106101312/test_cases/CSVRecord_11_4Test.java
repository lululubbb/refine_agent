package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Constructor;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

class CSVRecord_11_4Test {

    @Test
    @Timeout(8000)
    void testSize() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        String comment = "comment";
        long recordNumber = 1L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(
                String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);

        CSVRecord record = constructor.newInstance(values, mapping, comment, recordNumber);
        assertEquals(3, record.size());

        // Test with empty values array
        CSVRecord emptyRecord = constructor.newInstance(new String[0], Collections.emptyMap(), null, 2L);
        assertEquals(0, emptyRecord.size());
    }
}